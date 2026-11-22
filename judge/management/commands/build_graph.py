"""
解析 algorithm/**/*.md 中的 Obsidian [[链接]]，自动写入 AlgorithmEdge 表。

规则：
  - "前置知识" 章节下的 [[X]] → edge_type='prerequisite'  (X 是 source 的前置)
  - 正文其他位置的 [[X]] → edge_type='related'

用法：
  python manage.py build_graph [--dry-run] [--clear-auto]
"""
import os
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from judge.models import Algorithm, AlgorithmEdge

# ── 笔记文件名 / Obsidian 链接名 → algo_id 映射 ──────────────────
# 键：Obsidian 链接中出现的名称（不含 [[]]），或文件名（不含 .md）
# 值：judge_algorithm 表中的 algo_id
NOTE_TO_ALGO = {
    # 数据结构
    '并查集':         'union-find',
    '带权并查集':     'union-find',
    '种类并查集':     'union-find',
    '堆':            'heap',
    '对顶堆':        'heap',
    'ST表':          'sparse-table',
    '线段树':        'segment-tree',
    '懒标记线段树':  'segment-tree',
    '树状数组':      'bit',
    '单调栈':        'monotone-stack',
    '单调队列':      'monotone-queue',
    '栈':            'stack',
    '队列':          'queue',
    '链表':          'linked-list',
    '平衡树':        'balanced-tree',
    'Trie':          'trie',
    '字典树':        'trie',
    # 搜索
    'DFS':           'dfs',
    'BFS':           'bfs',
    '记忆化搜索':    'dfs',
    '迭代加深':      'dfs',
    '折半搜索':      'binary-search',
    # 图论
    'Dijkstra':      'dijkstra',
    'Floyd':         'floyd',
    'Floyd-Warshall':'floyd',
    'SPFA':          'shortest-path',
    'Kruskal':       'kruskal',
    'Prim':          'mst',
    '拓扑排序':      'topo-sort',
    '二分图判定':    'bipartite',
    '二分图最大匹配':'bipartite',
    '网络最大流':    'network-flow',
    'LCA':           'lca',
    '树的直径':      'tree-dp',
    '树链剖分':      'segment-tree',
    'Tarjan':        'graph-general',
    '割点与桥':      'graph-general',
    # 字符串
    'KMP':           'kmp',
    'AC自动机':      'aho-corasick',
    '字符串哈希':    'hashing',
    '后缀数组':      'suffix-array',
    'Manacher':      'kmp',   # 近似
    # 数学/数论
    '快速幂':        'fast-pow',
    '矩阵快速幂':    'matrix',
    '矩阵快速幂优化dp': 'matrix',
    '位运算':        'bitwise',
    '前缀和':        'prefix-sum',
    '差分':          'difference-array',
    '二阶差分':      'difference-array',
    '树上前缀和与差分': 'prefix-sum',
    '组合数':        'combinatorics',
    'GCD与LCM':      'number-theory',
    '模运算':        'number-theory',
    '乘法逆元':      'number-theory',
    '数论分块':      'number-theory',
    '中国剩余定理':  'number-theory',
    '莫比乌斯反演':  'number-theory',
    '埃氏筛':        'sieve',
    '欧拉筛':        'sieve',
    # 基础
    '双指针':        'two-pointers',
    '滑动窗口':      'two-pointers',
    '二分':          'binary-search',
    '二分查找':      'binary-search',
    '二分答案':      'binary-search',
    '三分':          'binary-search',
    '倍增':          'binary-lifting',
    '离散化':        'binary-search',
    '递归':          'recursion',
    '递推':          'recurrence',
    # 分治
    '普通分治':      'divide-conquer',
    'CDQ分治':       'divide-conquer',
    '整体二分':      'divide-conquer',
    '扫描线':        'divide-conquer',
    '分块':          'divide-conquer',
    '莫队':          'divide-conquer',
    # DP
    '动态规划':      'dp-general',
    '线性dp':        'dp-general',
    '状态机dp':      'dp-general',
    '计数dp':        'dp-general',
    '概率与期望dp':  'dp-general',
    '区间dp':        'interval-dp',
    '环形区间dp':    'interval-dp',
    '树形dp':        'tree-dp',
    '换根dp':        'tree-dp',
    '树上背包':      'tree-dp',
    '数位dp':        'digit-dp',
    '状压dp':        'bitmask-dp',
    '状压BFS':       'bitmask-dp',
    '最长上升子序列': 'lis',
    '最长公共子序列': 'lcs',
    '0-1背包':       'knapsack',
    '完全背包':      'knapsack',
    '多重背包':      'knapsack',
    '分组背包':      'knapsack',
    '单调队列优化dp':'dp-general',
    '数据结构优化dp':'dp-general',
    '斜率优化dp':    'dp-general',
    # 贪心
    '贪心':          'greedy',
    '排序贪心':      'greedy',
    '区间贪心':      'activity-select',
    '堆贪心':        'greedy',
    '反悔贪心':      'greedy',
    # 0-1 BFS / A* — 近似
    '0-1 BFS':       'bfs',
    'A∗':            'bfs',
    # 图基础
    '图':            'graph-general',
    '最短路':        'shortest-path',
    '最小生成树':    'mst',
}

# 前置知识章节的正则（匹配各种标题写法）
RE_PREREQ_SECTION = re.compile(
    r'^#{1,3}\s*前置知识', re.MULTILINE
)
RE_NEXT_SECTION = re.compile(r'^#{1,3}\s+\S', re.MULTILINE)
RE_WIKI_LINK = re.compile(r'\[\[([^\]|#]+?)(?:\|[^\]]*)?\]\]')


def extract_links(text: str):
    """
    返回 (prereq_links, other_links) 两个集合。
    prereq_links: "前置知识" 章节内的链接名
    other_links:  正文其余位置的链接名
    """
    prereq_links: set[str] = set()
    other_links:  set[str] = set()

    pm = RE_PREREQ_SECTION.search(text)
    if pm:
        section_start = pm.end()
        nm = RE_NEXT_SECTION.search(text, section_start)
        section_end = nm.start() if nm else len(text)
        prereq_text = text[section_start:section_end]
        other_text  = text[:pm.start()] + text[section_end:]
    else:
        prereq_text = ''
        other_text  = text

    for m in RE_WIKI_LINK.finditer(prereq_text):
        prereq_links.add(m.group(1).strip())
    for m in RE_WIKI_LINK.finditer(other_text):
        other_links.add(m.group(1).strip())

    other_links -= prereq_links   # 避免重复
    return prereq_links, other_links


class Command(BaseCommand):
    help = '解析 algorithm/**/*.md 中的 Obsidian [[链接]]，写入 AlgorithmEdge'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='只打印，不写库')
        parser.add_argument('--clear-auto', action='store_true',
                            help='先删除所有 edge_type=related/extends 的自动边')

    def handle(self, *args, **options):
        dry  = options['dry_run']
        algo_dir = Path(settings.BASE_DIR) / 'algorithm'
        if not algo_dir.exists():
            self.stderr.write(f'目录不存在: {algo_dir}')
            return

        if options['clear_auto'] and not dry:
            deleted, _ = AlgorithmEdge.objects.filter(
                edge_type__in=['related', 'extends']
            ).delete()
            self.stdout.write(f'已删除 {deleted} 条自动边')

        algo_map = {a.algo_id: a for a in Algorithm.objects.all()}

        created = skipped = missing_src = missing_tgt = unmatched_src = 0
        unmatched_links: set[str] = set()

        for md_path in sorted(algo_dir.rglob('*.md')):
            # 跳过模板 / 锦囊 / Map / README 等非算法文件
            rel = md_path.relative_to(algo_dir)
            parts = rel.parts
            if parts[0] in ('template', '锦囊', 'Map.md', 'README.md'):
                continue
            if md_path.name in ('Map.md', 'README.md'):
                continue

            filename = md_path.stem        # e.g. "Dijkstra", "并查集"
            src_id = NOTE_TO_ALGO.get(filename)
            if not src_id:
                unmatched_src += 1
                if options['verbosity'] >= 2:
                    self.stderr.write(f'[NO-SRC] {rel}  ({filename})')
                continue
            if src_id not in algo_map:
                missing_src += 1
                continue

            src_algo = algo_map[src_id]
            text = md_path.read_text(encoding='utf-8', errors='ignore')
            prereq_links, other_links = extract_links(text)

            for link_name in prereq_links:
                tgt_id = NOTE_TO_ALGO.get(link_name)
                if not tgt_id:
                    unmatched_links.add(link_name)
                    continue
                if tgt_id not in algo_map or tgt_id == src_id:
                    continue
                tgt_algo = algo_map[tgt_id]
                if not dry:
                    _, was_created = AlgorithmEdge.objects.get_or_create(
                        source=src_algo, target=tgt_algo,
                        defaults={'edge_type': 'prerequisite'},
                    )
                    if was_created: created += 1
                    else:           skipped += 1
                else:
                    self.stdout.write(f'  [prereq] {src_id} → {tgt_id}')
                    created += 1

            for link_name in other_links:
                tgt_id = NOTE_TO_ALGO.get(link_name)
                if not tgt_id:
                    unmatched_links.add(link_name)
                    continue
                if tgt_id not in algo_map or tgt_id == src_id:
                    continue
                tgt_algo = algo_map[tgt_id]
                if not dry:
                    _, was_created = AlgorithmEdge.objects.get_or_create(
                        source=src_algo, target=tgt_algo,
                        defaults={'edge_type': 'related'},
                    )
                    if was_created: created += 1
                    else:           skipped += 1
                else:
                    self.stdout.write(f'  [related] {src_id} → {tgt_id}')
                    created += 1

        if unmatched_links:
            self.stdout.write('\n[未匹配的链接名，可手动补充到 NOTE_TO_ALGO：]')
            for name in sorted(unmatched_links):
                self.stdout.write(f'  [[{name}]]')

        verb = '(dry-run) 将新建' if dry else '新建'
        self.stdout.write(self.style.SUCCESS(
            f'\n完成: {verb} {created} 条，已存在跳过 {skipped} 条，'
            f'未匹配源文件 {unmatched_src} 个，缺失 algo_id {missing_src} 个'
        ))
