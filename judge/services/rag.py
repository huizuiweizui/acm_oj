"""
RAG 检索与流式回答。

retrieve(query, algo_id=None, top_k=5)
  → 返回最相关的 KnowledgeChunk 列表

stream_answer(question, chunks)
  → 生成器，逐块 yield SSE 格式字节串
"""
import json

import numpy as np
import requests
from django.conf import settings

from judge.models import Algorithm, ChunkEmbedding, KnowledgeChunk

SYSTEM_PROMPT = (
    "你是一个算法竞赛学习助手，专注于帮助用户理解算法和数据结构。\n"
    "请基于提供的参考资料回答问题，回答要简洁清晰，面向初学者。\n"
    "如果参考资料中没有相关内容，请如实说明，不要编造。\n"
    "代码示例优先用 C++。"
)


# ── 向量检索 ──────────────────────────────────────────────────

def _cosine_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a: (D,)  b: (N, D)  → (N,)"""
    a_norm = a / (np.linalg.norm(a) + 1e-9)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return b_norm @ a_norm


def _embed_query(query: str) -> list[float] | None:
    """调用 Embedding API 对查询文本向量化，失败返回 None。"""
    from openai import OpenAI
    model = getattr(settings, 'EMBED_MODEL', '').strip()
    if not model:
        return None
    key  = getattr(settings, 'EMBED_API_KEY',  '').strip() \
           or getattr(settings, 'LLM_API_KEY',  '').strip()
    base = getattr(settings, 'EMBED_API_BASE', '').strip()
    if not base:
        llm_url = getattr(settings, 'LLM_API_URL', '').strip()
        base = llm_url.replace('/chat/completions', '') if llm_url else ''
    try:
        client = OpenAI(api_key=key, base_url=base)
        resp = client.embeddings.create(model=model, input=[query])
        return resp.data[0].embedding
    except Exception:
        return None


def _query_keywords(query: str) -> list[str]:
    """
    查询关键词。中文没有空格，按空白切会把整句当成一个词、基本匹配不到，
    所以优先用星语 skills 的 jieba 分词（术语与关键词提取）；没装 jieba 时退回按空白切分。
    """
    try:
        from star.skills import keywords, normalize, segment
    except ImportError:  # 没装 jieba 或没有 star 包：保持原来的行为
        return [w for w in query.split() if len(w) > 1]
    return keywords(segment(normalize(query)))


def retrieve(query: str, algo_id: str | None = None, top_k: int = 5) -> list[KnowledgeChunk]:
    """
    语义检索 top_k 最相关的 chunk。
    若没有 embedding 数据，退化为关键词匹配。
    """
    # —— 优先语义检索 ——
    q_vec = _embed_query(query)
    if q_vec is not None:
        qs = ChunkEmbedding.objects.select_related('chunk', 'chunk__algo').all()
        if algo_id:
            # 先取该算法的 chunk，若不足再从全库补
            algo_qs = qs.filter(chunk__algo__algo_id=algo_id)
            if algo_qs.count() >= top_k:
                qs = algo_qs

        embeddings = list(qs)
        if embeddings:
            mat = np.array([e.vector for e in embeddings], dtype=np.float32)
            q_arr = np.array(q_vec, dtype=np.float32)
            scores = _cosine_sim(q_arr, mat)
            top_idx = np.argsort(scores)[::-1][:top_k]
            return [embeddings[i].chunk for i in top_idx]

    # —— 退化：关键词匹配 ——
    qs = KnowledgeChunk.objects.select_related('algo')
    if algo_id:
        qs = qs.filter(algo__algo_id=algo_id)
    keywords = _query_keywords(query)
    if keywords:
        from django.db.models import Q
        q_filter = Q()
        for kw in keywords:
            q_filter |= Q(content__icontains=kw) | Q(section__icontains=kw)
        qs = qs.filter(q_filter)
    return list(qs[:top_k])


# ── 流式 LLM 调用 ─────────────────────────────────────────────

def stream_answer(question: str, chunks: list[KnowledgeChunk]):
    """
    生成器：yield SSE 格式字节串（data: {...}\\n\\n）。
    最后 yield b'data: [DONE]\\n\\n'。
    """
    key   = getattr(settings, 'LLM_API_KEY',  '').strip()
    url   = getattr(settings, 'LLM_API_URL',  '').strip()
    model = getattr(settings, 'LLM_MODEL',    '').strip()

    if not key or not url:
        payload = json.dumps({'text': '未配置 LLM_API_KEY / LLM_API_URL'}, ensure_ascii=False)
        yield f'data: {payload}\n\n'.encode()
        yield b'data: [DONE]\n\n'
        return

    context_parts = []
    for c in chunks:
        header = f'[来源：{c.source_file} § {c.section}]'
        context_parts.append(f'{header}\n{c.content}')
    context = '\n\n---\n\n'.join(context_parts)

    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user',   'content': f'参考资料：\n{context}\n\n问题：{question}'},
    ]

    try:
        resp = requests.post(
            url,
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json={'model': model, 'messages': messages, 'stream': True, 'temperature': 0.3},
            stream=True,
            timeout=60,
        )
        resp.raise_for_status()

        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode('utf-8', errors='ignore')
            if line.startswith('data:'):
                data_str = line[5:].strip()
                if data_str == '[DONE]':
                    break
                try:
                    chunk_data = json.loads(data_str)
                    delta = chunk_data['choices'][0]['delta']
                    text = delta.get('content', '')
                    if text:
                        payload = json.dumps({'text': text}, ensure_ascii=False)
                        yield f'data: {payload}\n\n'.encode()
                except (json.JSONDecodeError, KeyError):
                    continue

    except Exception as e:
        payload = json.dumps({'text': f'\n\n[错误：{e}]'}, ensure_ascii=False)
        yield f'data: {payload}\n\n'.encode()

    yield b'data: [DONE]\n\n'
