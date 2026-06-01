"""
对 KnowledgeChunk 调用 Embedding API，结果写入 ChunkEmbedding 表。

支持断点续跑（自动跳过已有向量的 chunk）。

用法：
  python manage.py build_embeddings [--batch 50] [--reset]

依赖 .env：
  EMBED_API_KEY  留空则复用 LLM_API_KEY
  EMBED_API_BASE 默认 https://ark.cn-beijing.volces.com/api/v3
  EMBED_MODEL    必须填写，如 ep-xxxxxx（Ark embedding 端点）
"""
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from openai import OpenAI

from judge.models import ChunkEmbedding, KnowledgeChunk


def _get_client():
    key  = getattr(settings, 'EMBED_API_KEY',  '').strip() \
           or getattr(settings, 'LLM_API_KEY',  '').strip()
    base = getattr(settings, 'EMBED_API_BASE', '').strip()
    if not base:
        # 从 LLM_API_URL 推导 base（去掉末尾的 /chat/completions）
        llm_url = getattr(settings, 'LLM_API_URL', '').strip()
        base = llm_url.replace('/chat/completions', '') if llm_url else ''
    if not key:
        raise RuntimeError('未配置 EMBED_API_KEY / LLM_API_KEY')
    return OpenAI(api_key=key, base_url=base)


def _embed_batch(client, model, texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(model=model, input=texts)
    # 按 index 排序保证顺序
    items = sorted(resp.data, key=lambda x: x.index)
    return [item.embedding for item in items]


class Command(BaseCommand):
    help = '对所有 KnowledgeChunk 生成 embedding 向量并写入 ChunkEmbedding'

    def add_arguments(self, parser):
        parser.add_argument('--batch', type=int, default=32,
                            help='每次 API 调用的 chunk 数（默认 32）')
        parser.add_argument('--reset', action='store_true',
                            help='先删除所有已有 embedding，重新生成')

    def handle(self, *args, **options):
        model = getattr(settings, 'EMBED_MODEL', '').strip()
        if not model:
            self.stderr.write(self.style.ERROR(
                '请在 .env 中设置 EMBED_MODEL（Ark embedding 端点 ID）后再运行'
            ))
            return

        try:
            client = _get_client()
        except RuntimeError as e:
            self.stderr.write(self.style.ERROR(str(e)))
            return

        if options['reset']:
            deleted, _ = ChunkEmbedding.objects.all().delete()
            self.stdout.write(f'已删除 {deleted} 条旧 embedding')

        # 只处理还没有 embedding 的 chunk
        done_ids = set(ChunkEmbedding.objects.values_list('chunk_id', flat=True))
        pending = list(KnowledgeChunk.objects.exclude(id__in=done_ids).order_by('id'))

        if not pending:
            self.stdout.write('所有 chunk 都已有 embedding，无需重新生成。')
            return

        self.stdout.write(f'待处理 {len(pending)} 个 chunk，batch={options["batch"]}，model={model}')

        batch_size = options['batch']
        created = errors = 0

        for i in range(0, len(pending), batch_size):
            batch = pending[i:i + batch_size]
            texts = [
                f'[来源：{c.source_file} § {c.section}]\n{c.content[:1200]}'
                for c in batch
            ]
            try:
                vectors = _embed_batch(client, model, texts)
            except Exception as e:
                self.stderr.write(f'[ERROR] batch {i//batch_size + 1}: {e}')
                errors += len(batch)
                time.sleep(2)
                continue

            objs = [
                ChunkEmbedding(chunk=chunk, vector=vec, model_name=model)
                for chunk, vec in zip(batch, vectors)
            ]
            ChunkEmbedding.objects.bulk_create(objs)
            created += len(objs)

            progress = min(i + batch_size, len(pending))
            self.stdout.write(f'  [{progress}/{len(pending)}] +{len(objs)} embedding')

        self.stdout.write(self.style.SUCCESS(
            f'\n完成: 新建 {created} 条，失败 {errors} 条'
        ))
