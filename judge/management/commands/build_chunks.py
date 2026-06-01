"""
解析 algorithm/**/*.md，按二级标题（##）切分为知识片段，写入 KnowledgeChunk 表。

用法：
  python manage.py build_chunks [--clear] [--dry-run]
"""
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from judge.models import Algorithm, KnowledgeChunk
from judge.management.commands.build_graph import NOTE_TO_ALGO   # 复用文件名→algo_id 映射

RE_H2 = re.compile(r'^##\s+(.+)$', re.MULTILINE)
# 跳过 Obsidian frontmatter 中的难度标签行
RE_FRONTMATTER = re.compile(r'^#难度/.*$', re.MULTILINE)

SKIP_DIRS = {'template', '锦囊'}
SKIP_FILES = {'Map.md', 'README.md'}

# 粗略估算：1 汉字≈2 token，1 ASCII 字符≈0.3 token
def _estimate_tokens(text: str) -> int:
    cn = sum(1 for c in text if '一' <= c <= '鿿')
    ascii_chars = len(text) - cn
    return int(cn * 2 + ascii_chars * 0.3)


def _split_chunks(text: str, source_name: str) -> list[dict]:
    """
    按 ## 标题拆分，返回 [{section, content, token_count}, ...]。
    首段（## 之前）作为 section='概述'。
    """
    text = RE_FRONTMATTER.sub('', text).strip()
    matches = list(RE_H2.finditer(text))
    chunks = []

    def _add(section, body):
        body = body.strip()
        if not body:
            return
        # 控制单块大小：超过 800 token 的按段落二次切分
        if _estimate_tokens(body) <= 800:
            chunks.append({'section': section, 'content': body,
                           'token_count': _estimate_tokens(body)})
        else:
            paras = re.split(r'\n{2,}', body)
            buf, buf_tok = [], 0
            for para in paras:
                pt = _estimate_tokens(para)
                if buf_tok + pt > 800 and buf:
                    joined = '\n\n'.join(buf)
                    chunks.append({'section': section, 'content': joined,
                                   'token_count': _estimate_tokens(joined)})
                    buf, buf_tok = [para], pt
                else:
                    buf.append(para)
                    buf_tok += pt
            if buf:
                joined = '\n\n'.join(buf)
                chunks.append({'section': section, 'content': joined,
                               'token_count': _estimate_tokens(joined)})

    if matches:
        intro = text[:matches[0].start()]
        _add('概述', intro)
        for i, m in enumerate(matches):
            section_title = m.group(1).strip()
            body_start = m.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            _add(section_title, text[body_start:body_end])
    else:
        _add('全文', text)

    return chunks


class Command(BaseCommand):
    help = '解析 algorithm/**/*.md，写入 KnowledgeChunk'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='先清空 KnowledgeChunk 表')
        parser.add_argument('--dry-run', action='store_true', help='只统计，不写库')

    def handle(self, *args, **options):
        dry = options['dry_run']
        algo_dir = Path(settings.BASE_DIR) / 'algorithm'
        if not algo_dir.exists():
            self.stderr.write(f'目录不存在: {algo_dir}')
            return

        if options['clear'] and not dry:
            deleted, _ = KnowledgeChunk.objects.all().delete()
            self.stdout.write(f'已清空 {deleted} 条 chunk')

        algo_map = {a.algo_id: a for a in Algorithm.objects.all()}
        total_files = total_chunks = skipped_files = 0

        for md_path in sorted(algo_dir.rglob('*.md')):
            rel = md_path.relative_to(algo_dir)
            parts = rel.parts
            if parts[0] in SKIP_DIRS or md_path.name in SKIP_FILES:
                continue

            filename = md_path.stem
            algo_id = NOTE_TO_ALGO.get(filename)
            algo_obj = algo_map.get(algo_id) if algo_id else None

            text = md_path.read_text(encoding='utf-8', errors='ignore')
            chunks = _split_chunks(text, filename)
            if not chunks:
                skipped_files += 1
                continue

            total_files += 1
            if dry:
                self.stdout.write(f'{rel}  ({algo_id or "??"})  → {len(chunks)} chunks')
                for c in chunks:
                    self.stdout.write(f'    [{c["token_count"]:>4} tok] {c["section"][:60]}')
                total_chunks += len(chunks)
                continue

            for c in chunks:
                KnowledgeChunk.objects.create(
                    source_file=str(rel),
                    algo=algo_obj,
                    section=c['section'],
                    content=c['content'],
                    token_count=c['token_count'],
                )
            total_chunks += len(chunks)

        verb = '(dry-run) 将写入' if dry else '已写入'
        self.stdout.write(self.style.SUCCESS(
            f'\n完成: {total_files} 个文件 → {verb} {total_chunks} 个 chunk'
            + (f'，跳过空文件 {skipped_files} 个' if skipped_files else '')
        ))
