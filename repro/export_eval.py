"""
在跑过 star_eval 的环境里执行（python manage.py shell < repro/export_eval.py），导出复现所需的原始数据：

    /tmp/repro_export/llm_calls.jsonl   全部大模型调用日志（演示数据预生成 + 四组实验），每行一条
    /tmp/repro_export/embeddings.json   一致性实验里每个回答的 bge-m3 向量，离线复算余弦相似度用

调用日志里学习者姓名在出平台前已替换成 {name}；实验用的学习者都是虚构的。
"""
import json
from pathlib import Path

from django.conf import settings

from judge.services.rag import _embed_query
from star.models import LLMCallLog
from star.services.llm import parse_json

OUT = Path('/tmp/repro_export')
OUT.mkdir(exist_ok=True)

rows = []
for log in LLMCallLog.objects.order_by('id'):
    rows.append({
        'id': log.id, 'purpose': log.purpose, 'tag': log.tag, 'attempt': log.attempt,
        'request': log.request, 'response': log.response, 'error': log.error,
        'duration_ms': log.duration_ms, 'prompt_tokens': log.prompt_tokens,
        'completion_tokens': log.completion_tokens, 'total_tokens': log.total_tokens,
        'passed': log.passed, 'checks': log.checks, 'created_at': log.created_at.isoformat(),
    })
with open(OUT / 'llm_calls.jsonl', 'w', encoding='utf-8') as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

texts = []
for r in rows:
    if r['tag'].startswith('eval:consistency:'):
        d = parse_json(r['response']) or {}
        t = f'{d.get("reply", "")} / {"、".join(d.get("options") or [])}'
        if t not in texts:
            texts.append(t)
vectors = {}
for t in texts:
    v = _embed_query(t)
    vectors[t] = [round(float(x), 7) for x in v] if v is not None else None
(OUT / 'embeddings.json').write_text(json.dumps(
    {'model': settings.EMBED_MODEL, 'vectors': vectors}, ensure_ascii=False), encoding='utf-8')

print('calls', len(rows), 'texts', len(texts), 'embedded', sum(1 for v in vectors.values() if v),
      'model', settings.LLM_MODEL, settings.EMBED_MODEL)
