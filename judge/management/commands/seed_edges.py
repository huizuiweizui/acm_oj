"""
手动维护的算法关系边，运行后写入 AlgorithmEdge 表。
用法：python manage.py seed_edges [--clear]
"""
from django.core.management.base import BaseCommand
from judge.models import Algorithm, AlgorithmEdge

MANUAL_EDGES = [
    # prerequisite: source 是 target 的前置知识
    ('dijkstra',       'heap',           'prerequisite'),
    ('dijkstra',       'shortest-path',  'extends'),
    ('kruskal',        'union-find',     'prerequisite'),
    ('kruskal',        'mst',            'extends'),
    ('bitmask-dp',     'bitwise',        'prerequisite'),
    ('bitmask-dp',     'dp-general',     'extends'),
    ('segment-tree',   'divide-conquer', 'prerequisite'),
    ('lca',            'dfs',            'prerequisite'),
    ('lca',            'sparse-table',   'prerequisite'),
    ('aho-corasick',   'trie',           'extends'),
    ('aho-corasick',   'kmp',            'extends'),
    ('merge-sort',     'divide-conquer', 'extends'),
    ('quick-sort',     'divide-conquer', 'extends'),
    ('heap-sort',      'heap',           'prerequisite'),
    ('lis',            'binary-search',  'prerequisite'),
    ('lis',            'dp-general',     'extends'),
    ('matrix',         'fast-pow',       'prerequisite'),
    ('floyd',          'dp-general',     'extends'),
    ('tree-dp',        'dfs',            'prerequisite'),
    ('tree-dp',        'dp-general',     'extends'),
    ('knapsack',       'dp-general',     'extends'),
    ('lcs',            'dp-general',     'extends'),
    ('interval-dp',    'dp-general',     'extends'),
    ('digit-dp',       'dp-general',     'extends'),
    ('network-flow',   'graph-general',  'extends'),
    ('bipartite',      'graph-general',  'extends'),
    ('bipartite',      'bfs',            'prerequisite'),
    ('topo-sort',      'graph-general',  'prerequisite'),
    ('topo-sort',      'bfs',            'prerequisite'),
    ('mst',            'graph-general',  'prerequisite'),
    ('shortest-path',  'graph-general',  'prerequisite'),
    ('dfs',            'recursion',      'prerequisite'),
    ('bfs',            'queue',          'prerequisite'),
    ('binary-search',  'two-pointers',   'related'),
    ('prefix-sum',     'difference-array', 'related'),
    ('monotone-stack', 'stack',          'prerequisite'),
    ('monotone-queue', 'queue',          'prerequisite'),
    ('sparse-table',   'prefix-sum',     'extends'),
    ('suffix-array',   'binary-search',  'prerequisite'),
    ('kmp',            'brute-force',    'extends'),
    ('fast-pow',       'recursion',      'prerequisite'),
    ('divide-conquer', 'recursion',      'extends'),
    ('activity-select','greedy',         'extends'),
    ('game-theory',    'dp-general',     'related'),
    ('probability',    'combinatorics',  'prerequisite'),
    ('number-theory',  'fast-pow',       'related'),
    ('heap',           'sort-general',   'related'),
    ('bit',            'bitwise',        'prerequisite'),
]


class Command(BaseCommand):
    help = '写入手动维护的算法关系边'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='先清空表再写入')

    def handle(self, *args, **options):
        if options['clear']:
            deleted, _ = AlgorithmEdge.objects.all().delete()
            self.stdout.write(f'已清空 {deleted} 条边')

        algo_map = {a.algo_id: a for a in Algorithm.objects.all()}
        created = skipped = missing = 0

        for src_id, tgt_id, etype in MANUAL_EDGES:
            if src_id not in algo_map:
                self.stderr.write(f'[MISS] 未找到算法: {src_id}')
                missing += 1
                continue
            if tgt_id not in algo_map:
                self.stderr.write(f'[MISS] 未找到算法: {tgt_id}')
                missing += 1
                continue
            _, was_created = AlgorithmEdge.objects.get_or_create(
                source=algo_map[src_id],
                target=algo_map[tgt_id],
                defaults={'edge_type': etype},
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'完成: 新建 {created} 条，已存在跳过 {skipped} 条，缺失算法 {missing} 处'
        ))
