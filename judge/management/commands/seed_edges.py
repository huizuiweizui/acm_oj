"""
手动维护的算法关系边，运行后写入 AlgorithmEdge 表。

边语义约定：
  prerequisite: target 是学习 source 的前置知识（必须先学 target，才能学 source）
  extends:      source 是 target 的进阶 / 具体实现（source 建立在 target 的思路之上）
  related:      双向关联，同类问题或常配合使用，无严格顺序依赖

用法：
  python manage.py seed_edges           # 幂等写入（已存在的边跳过）
  python manage.py seed_edges --clear   # 先清空全表再写入（修正 edge_type 时使用）
"""
from django.core.management.base import BaseCommand
from judge.models import Algorithm, AlgorithmEdge

MANUAL_EDGES = [
    # ================================================================
    # 基础算法 — 递归 / 递推 / 分治是众多算法的共同基石
    # ================================================================
    ('dfs',             'recursion',      'prerequisite'),   # DFS 用递归实现
    ('divide-conquer',  'recursion',      'prerequisite'),   # 分治用递归拆解子问题
    ('fast-pow',        'recursion',      'prerequisite'),   # 快速幂递归版本
    ('recurrence',      'recursion',      'related'),        # 递推与递归互为对偶思维
    ('dp-general',      'recurrence',     'prerequisite'),   # DP 本质是带记忆的递推
    ('fast-pow',        'recurrence',     'extends'),        # 快速幂基于 a^n = a^(n/2)² 递推关系
    ('binary-search',   'two-pointers',   'related'),        # 同属"索引缩减"类技巧

    # ================================================================
    # 排序 — 各排序算法是 sort-general 概念的具体实现
    # ================================================================
    ('bubble-sort',     'sort-general',   'extends'),
    ('quick-sort',      'sort-general',   'extends'),
    ('merge-sort',      'sort-general',   'extends'),
    ('heap-sort',       'sort-general',   'extends'),
    ('heap-sort',       'heap',           'prerequisite'),   # 堆排序需要掌握堆数据结构
    ('quick-sort',      'divide-conquer', 'extends'),        # 快速排序是分治的典型应用
    ('merge-sort',      'divide-conquer', 'extends'),        # 归并排序是分治的典型应用

    # ================================================================
    # 搜索 — 二分 / DFS / BFS 各有明确前置
    # ================================================================
    ('binary-search',   'sort-general',   'prerequisite'),   # 二分查找要求序列有序
    ('dfs',             'graph-general',  'prerequisite'),   # 图 DFS 需要图论基础
    ('bfs',             'graph-general',  'prerequisite'),   # 图 BFS 需要图论基础
    ('bfs',             'queue',          'prerequisite'),   # BFS 用队列维护层序遍历
    ('dfs',             'search-general', 'extends'),        # DFS 是深度优先搜索的具体实现
    ('bfs',             'search-general', 'extends'),        # BFS 是广度优先搜索的具体实现
    ('binary-search',   'search-general', 'extends'),        # 二分是有序空间上的高效搜索

    # ================================================================
    # 贪心 — 活动选择是贪心策略的经典例题
    # ================================================================
    ('activity-select', 'greedy',         'extends'),
    ('activity-select', 'sort-general',   'prerequisite'),   # 活动选择先按截止时间排序

    # ================================================================
    # 动态规划 — dp-general 是所有 DP 变种的共同基础
    # ================================================================
    ('knapsack',        'dp-general',     'extends'),
    ('lcs',             'dp-general',     'extends'),
    ('lis',             'dp-general',     'extends'),
    ('lis',             'binary-search',  'prerequisite'),   # O(n log n) LIS 用二分优化
    ('bitmask-dp',      'dp-general',     'prerequisite'),   # 状压 DP 以 DP 思想为基础
    ('bitmask-dp',      'bitwise',        'prerequisite'),   # 状压 DP 用位运算枚举子集
    ('interval-dp',     'dp-general',     'extends'),
    ('tree-dp',         'dp-general',     'extends'),
    ('tree-dp',         'dfs',            'prerequisite'),   # 树形 DP 用 DFS 遍历树结构
    ('digit-dp',        'dp-general',     'extends'),
    ('floyd',           'dp-general',     'extends'),        # Floyd 是 DP 在图上的应用
    ('game-theory',     'dp-general',     'related'),        # 博弈论常用 DP 记忆化求解

    # ================================================================
    # 图论 — 核心算法层层依赖
    # ================================================================
    ('shortest-path',   'graph-general',  'prerequisite'),   # 最短路问题需要图论基础
    ('dijkstra',        'shortest-path',  'prerequisite'),   # Dijkstra 是最短路的一种算法
    ('dijkstra',        'heap',           'prerequisite'),   # 优先队列加速 Dijkstra
    ('dijkstra',        'graph-general',  'prerequisite'),
    ('floyd',           'shortest-path',  'prerequisite'),   # Floyd 是全源最短路算法
    ('mst',             'graph-general',  'prerequisite'),   # 最小生成树问题需要图论基础
    ('kruskal',         'union-find',     'prerequisite'),   # Kruskal 用并查集合并连通分量
    ('kruskal',         'mst',            'extends'),        # Kruskal 是 MST 的一种实现
    ('kruskal',         'graph-general',  'prerequisite'),
    ('topo-sort',       'graph-general',  'prerequisite'),
    ('topo-sort',       'bfs',            'prerequisite'),   # Kahn 算法（拓扑排序）基于 BFS
    ('network-flow',    'graph-general',  'extends'),
    ('network-flow',    'bfs',            'prerequisite'),   # Edmonds-Karp 增广路用 BFS
    ('bipartite',       'graph-general',  'extends'),
    ('bipartite',       'bfs',            'prerequisite'),   # 二分图染色法用 BFS 遍历
    ('bipartite',       'network-flow',   'related'),        # 二分图最大匹配 = 最大流特例
    ('lca',             'dfs',            'prerequisite'),
    ('lca',             'sparse-table',   'prerequisite'),   # 倍增 LCA 需要 Sparse Table

    # ================================================================
    # 数据结构 — 高级结构依赖基础结构或算法思想
    # ================================================================
    ('monotone-stack',  'stack',          'prerequisite'),
    ('monotone-queue',  'queue',          'prerequisite'),
    ('heap',            'sort-general',   'related'),        # 堆与排序强关联
    ('bit',             'bitwise',        'prerequisite'),   # 树状数组依赖 lowbit 位运算
    ('segment-tree',    'divide-conquer', 'prerequisite'),   # 线段树基于分治思想
    ('sparse-table',    'prefix-sum',     'extends'),        # Sparse Table 是 RMQ 版前缀积
    ('trie',            'hashing',        'related'),        # 字典树与哈希同为字符串索引结构
    ('union-find',      'graph-general',  'related'),        # 并查集大量用于图连通性问题

    # ================================================================
    # 字符串 — 匹配算法层层递进
    # ================================================================
    ('kmp',             'brute-force',    'extends'),        # KMP 是暴力匹配的线性优化
    ('kmp',             'hashing',        'related'),        # 两种字符串精确匹配的主要思路
    ('suffix-array',    'binary-search',  'prerequisite'),   # 后缀数组上的查询需要二分
    ('suffix-array',    'hashing',        'related'),        # 后缀数组与字符串哈希互补
    ('aho-corasick',    'trie',           'extends'),        # AC 自动机在字典树上构建失配指针
    ('aho-corasick',    'kmp',            'extends'),        # AC 自动机是 KMP 的多模式推广

    # ================================================================
    # 数学 — 数论 / 组合 / 线性技巧的依赖关系
    # ================================================================
    ('difference-array','prefix-sum',     'prerequisite'),   # 差分数组用前缀和还原原数组
    ('fast-pow',        'bitwise',        'related'),        # 快速幂常用位运算判断奇偶
    ('matrix',          'fast-pow',       'prerequisite'),   # 矩阵快速幂（线性递推加速）
    ('sieve',           'enumeration',    'extends'),        # 线性筛是聪明的枚举优化
    ('number-theory',   'fast-pow',       'related'),        # 费马小定理用快速幂求逆元
    ('number-theory',   'sieve',          'prerequisite'),   # 数论需要质数筛法
    ('combinatorics',   'fast-pow',       'prerequisite'),   # C(n,r) mod p 需快速幂求阶乘逆元
    ('probability',     'combinatorics',  'prerequisite'),   # 概率论建立在组合数基础上
    ('big-integer',     'recurrence',     'related'),        # 高精度按位逐步递推处理
]


class Command(BaseCommand):
    help = '写入手动维护的算法关系边（prerequisite / extends / related）'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='先清空全表再写入（用于修正 edge_type）')

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
