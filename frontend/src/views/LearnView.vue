<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

// ── 数据 ───────────────────────────────────────────────────────
const CATEGORIES = ['全部', '基础算法', '排序', '搜索', '贪心', '动态规划', '图论', '数据结构', '字符串', '数学']

const ALGORITHMS = [
  { id:'simulation',      name:'模拟',           nameEn:'Simulation',             category:'基础算法', difficulty:'入门', desc:'按题意直接逐步模拟，适合逻辑清晰的过程性问题，无需特殊技巧。' },
  { id:'enumeration',     name:'枚举',           nameEn:'Enumeration',            category:'基础算法', difficulty:'入门', desc:'穷举所有合法情况逐一判断，搜索空间有限时可直接给出答案。' },
  { id:'brute-force',     name:'暴力',           nameEn:'Brute Force',            category:'基础算法', difficulty:'入门', desc:'不加剪枝地枚举所有方案，是理解问题和验证最优解的基准方法。' },
  { id:'recurrence',      name:'递推',           nameEn:'Recurrence',             category:'基础算法', difficulty:'入门', desc:'根据前若干项的规律推导下一项，Fibonacci 数列是最典型的递推模型。' },
  { id:'recursion',       name:'递归',           nameEn:'Recursion',              category:'基础算法', difficulty:'入门', desc:'函数调用自身解决规模更小的子问题，需定义递归基避免无限递归。' },
  { id:'divide-conquer',  name:'分治',           nameEn:'Divide & Conquer',       category:'基础算法', difficulty:'提高', desc:'将问题分解为独立子问题分别求解再合并，归并排序与 FFT 是典型应用。' },
  { id:'two-pointers',    name:'双指针',         nameEn:'Two Pointers',           category:'基础算法', difficulty:'入门', desc:'用两个指针在数组中协同移动，O(n) 解决滑动窗口、求和对等问题。' },
  { id:'sort-general',    name:'排序',           nameEn:'Sorting',                category:'排序',     difficulty:'入门', desc:'将序列按规则重排，包括比较类（快排 O(n log n)）和非比较类（计数排序 O(n+k)）。' },
  { id:'bubble-sort',     name:'冒泡排序',       nameEn:'Bubble Sort',            category:'排序',     difficulty:'入门', desc:'重复交换相邻逆序元素，最大值逐步冒泡至末尾，可用无交换标志提前退出。' },
  { id:'quick-sort',      name:'快速排序',       nameEn:'Quick Sort',             category:'排序',     difficulty:'提高', desc:'分治思想，选取基准将数组分为两段递归排序，期望 O(n log n)，原地不稳定。' },
  { id:'merge-sort',      name:'归并排序',       nameEn:'Merge Sort',             category:'排序',     difficulty:'提高', desc:'稳定的分治排序，拆分后有序合并，O(n log n)，常用于逆序对计数与外排序。' },
  { id:'heap-sort',       name:'堆排序',         nameEn:'Heap Sort',              category:'排序',     difficulty:'提高', desc:'利用最大堆原地实现 O(n log n) 排序，不稳定，额外空间 O(1)。' },
  { id:'search-general',  name:'搜索',           nameEn:'Search',                 category:'搜索',     difficulty:'入门', desc:'在状态空间或序列中系统探索以找到目标解，DFS 和 BFS 是最核心的两种策略。' },
  { id:'binary-search',   name:'二分',           nameEn:'Binary Search',          category:'搜索',     difficulty:'入门', desc:'在有序区间每次折半定位目标，O(log n) 查找，二分答案是其重要扩展。' },
  { id:'dfs',             name:'深搜DFS',        nameEn:'Depth-First Search',     category:'搜索',     difficulty:'提高', desc:'沿路径尽可能深入，回溯后探索下一分支，适用于连通性判断、路径搜索与拓扑。' },
  { id:'bfs',             name:'广搜BFS',        nameEn:'Breadth-First Search',   category:'搜索',     difficulty:'提高', desc:'逐层扩展，天然保证无权图最短步数，适用于最短路与层序遍历。' },
  { id:'greedy',          name:'贪心',           nameEn:'Greedy Algorithm',       category:'贪心',     difficulty:'提高', desc:'每步做局部最优决策，若局部最优能推出全局最优则策略成立，需严格证明正确性。' },
  { id:'activity-select', name:'活动选择',       nameEn:'Activity Selection',     category:'贪心',     difficulty:'提高', desc:'按结束时间排序，每次选不冲突的最早结束活动，贪心策略经典入门题。' },
  { id:'dp-general',      name:'动态规划',       nameEn:'Dynamic Programming',    category:'动态规划', difficulty:'提高', desc:'把大问题拆分为重叠子问题，记忆化或递推避免重复计算，是竞赛核心算法。' },
  { id:'knapsack',        name:'背包',           nameEn:'Knapsack DP',            category:'动态规划', difficulty:'提高', desc:'01/完全背包经典 DP，容量限制下求最大价值，滚动数组优化至 O(W) 空间。' },
  { id:'lcs',             name:'最长公共子序列', nameEn:'LCS',                    category:'动态规划', difficulty:'进阶', desc:'二维 DP 求两序列最长公共子序列，O(nm)，是 diff 工具的核心算法。' },
  { id:'lis',             name:'最长递增子序列', nameEn:'LIS',                    category:'动态规划', difficulty:'进阶', desc:'经典 DP 可用二分+贪心优化至 O(n log n)，维护最优末尾序列。' },
  { id:'bitmask-dp',      name:'状压DP',         nameEn:'Bitmask DP',             category:'动态规划', difficulty:'进阶', desc:'用二进制位压缩集合状态，将指数级状态空间压缩，适用于小集合枚举问题。' },
  { id:'interval-dp',     name:'区间DP',         nameEn:'Interval DP',            category:'动态规划', difficulty:'进阶', desc:'以区间 [l,r] 为状态从小到大扩展，典型题有石子合并、矩阵链乘。' },
  { id:'tree-dp',         name:'树形DP',         nameEn:'Tree DP',                category:'动态规划', difficulty:'进阶', desc:'在树上做 DP，DFS 过程中自底向上合并子树信息，处理树上路径、选点等问题。' },
  { id:'digit-dp',        name:'数位DP',         nameEn:'Digit DP',               category:'动态规划', difficulty:'进阶', desc:'按数字每一位从高到低做 DP，统计 [l,r] 内满足数位条件的整数个数。' },
  { id:'graph-general',   name:'图论',           nameEn:'Graph Theory',           category:'图论',     difficulty:'提高', desc:'研究顶点与边构成的图，涵盖遍历、最短路、最小生成树、网络流等核心算法。' },
  { id:'shortest-path',   name:'最短路',         nameEn:'Shortest Path',          category:'图论',     difficulty:'提高', desc:'求图中两点路径的最小权重，Dijkstra 处理非负权，Bellman-Ford 支持负权。' },
  { id:'mst',             name:'最小生成树',     nameEn:'Minimum Spanning Tree',  category:'图论',     difficulty:'提高', desc:'连通所有节点且总边权最小的树，Kruskal 按边权排序，Prim 从节点扩展。' },
  { id:'topo-sort',       name:'拓扑排序',       nameEn:'Topological Sort',       category:'图论',     difficulty:'提高', desc:'对有向无环图线性排序，Kahn（BFS）与 DFS 两种写法，处理任务依赖关系。' },
  { id:'network-flow',    name:'网络流',         nameEn:'Network Flow',           category:'图论',     difficulty:'进阶', desc:'有向图中从源到汇的最大流，Dinic 算法 O(V²E)，是许多规划问题的建模工具。' },
  { id:'bipartite',       name:'二分图',         nameEn:'Bipartite Graph',        category:'图论',     difficulty:'进阶', desc:'顶点可二着色的图，匈牙利算法求最大匹配，König 定理联系最大匹配与最小覆盖。' },
  { id:'lca',             name:'LCA',            nameEn:'Lowest Common Ancestor', category:'图论',     difficulty:'提高', desc:'求树中两节点最近公共祖先，倍增 LCA 是竞赛主流实现，O(n log n)+O(log n)。' },
  { id:'dijkstra',        name:'Dijkstra',       nameEn:"Dijkstra's Algorithm",   category:'图论',     difficulty:'进阶', desc:'贪心 + 优先队列，非负权图单源最短路，O((V+E) log V)，竞赛最常用。' },
  { id:'floyd',           name:'Floyd-Warshall', nameEn:'Floyd-Warshall',         category:'图论',     difficulty:'提高', desc:'三重循环求所有点对最短路，O(V³)，支持负权不支持负环，代码极简。' },
  { id:'kruskal',         name:"Kruskal",        nameEn:"Kruskal's MST",          category:'图论',     difficulty:'进阶', desc:'按边权升序贪心加边，并查集判环，O(E log E) 构造最小生成树。' },
  { id:'stack',           name:'栈',             nameEn:'Stack',                  category:'数据结构', difficulty:'入门', desc:'后进先出（LIFO）线性结构，支持 push/pop，用于括号匹配、表达式求值、DFS。' },
  { id:'queue',           name:'队列',           nameEn:'Queue',                  category:'数据结构', difficulty:'入门', desc:'先进先出（FIFO）线性结构，BFS 的核心工具，双端队列支持两端 O(1) 操作。' },
  { id:'heap',            name:'堆',             nameEn:'Heap',                   category:'数据结构', difficulty:'提高', desc:'完全二叉树实现的优先队列，O(log n) 插入和提取极值，支撑堆排序和 Dijkstra。' },
  { id:'bit',             name:'树状数组',       nameEn:'Fenwick Tree (BIT)',      category:'数据结构', difficulty:'提高', desc:'O(log n) 单点修改与前缀和查询，代码精简，常用于逆序对统计与区间求和。' },
  { id:'segment-tree',    name:'线段树',         nameEn:'Segment Tree',           category:'数据结构', difficulty:'进阶', desc:'区间查询与区间修改，O(log n) 支持区间求和、最值，懒标记处理区间修改。' },
  { id:'union-find',      name:'并查集',         nameEn:'Union-Find (DSU)',        category:'数据结构', difficulty:'提高', desc:'路径压缩 + 按秩合并，均摊近似 O(1) 的集合合并与连通性查询。' },
  { id:'trie',            name:'字典树',         nameEn:'Trie',                   category:'数据结构', difficulty:'提高', desc:'前缀树结构，O(m) 插入与查询，用于词典、自动补全和字符串集合管理。' },
  { id:'monotone-stack',  name:'单调栈',         nameEn:'Monotone Stack',         category:'数据结构', difficulty:'提高', desc:'维护单调递增/递减序的栈，O(n) 处理每个元素的下一个更大/更小元素问题。' },
  { id:'monotone-queue',  name:'单调队列',       nameEn:'Monotone Queue',         category:'数据结构', difficulty:'提高', desc:'双端队列维护滑动窗口极值，O(n) 解决定长窗口最值，是单调栈的队列版本。' },
  { id:'sparse-table',    name:'ST表',           nameEn:'Sparse Table',           category:'数据结构', difficulty:'提高', desc:'倍增预处理区间最值，O(n log n) 建表后 O(1) 回答 RMQ 查询，不支持修改。' },
  { id:'hashing',         name:'哈希',           nameEn:'Hashing',                category:'字符串',   difficulty:'提高', desc:'多项式哈希将字符串映射为整数，O(1) 比较任意子串，是快速字符串比较的利器。' },
  { id:'kmp',             name:'KMP',            nameEn:'KMP Algorithm',          category:'字符串',   difficulty:'进阶', desc:'部分匹配表避免冗余比较，O(n+m) 线性时间完成字符串模式匹配。' },
  { id:'suffix-array',    name:'后缀数组',       nameEn:'Suffix Array',           category:'字符串',   difficulty:'进阶', desc:'字典序排列所有后缀，结合 LCP 数组可处理最长公共子串等复杂字符串问题。' },
  { id:'aho-corasick',    name:'AC自动机',       nameEn:'Aho-Corasick',           category:'字符串',   difficulty:'进阶', desc:'在 Trie 上加失配指针，O(n+m) 同时在文本中搜索多个模式串。' },
  { id:'prefix-sum',      name:'前缀和',         nameEn:'Prefix Sum',             category:'数学',     difficulty:'入门', desc:'O(n) 预处理后 O(1) 回答区间和，可扩展为二维前缀和处理矩阵区域查询。' },
  { id:'difference-array',name:'差分',           nameEn:'Difference Array',       category:'数学',     difficulty:'入门', desc:'差分数组支持 O(1) 区间加法、O(n) 复原，是前缀和的逆运算，处理区间修改。' },
  { id:'fast-pow',        name:'快速幂',         nameEn:'Fast Exponentiation',    category:'数学',     difficulty:'入门', desc:'反复平方将幂运算从 O(n) 降至 O(log n)，取模快速幂是竞赛必备技巧。' },
  { id:'sieve',           name:'线性筛',         nameEn:"Euler's Sieve",          category:'数学',     difficulty:'提高', desc:'每个合数只被最小质因子筛一次，O(n) 线性时间筛出 n 以内全部素数。' },
  { id:'number-theory',   name:'数论',           nameEn:'Number Theory',          category:'数学',     difficulty:'提高', desc:'研究整数性质，包括质数筛、GCD/LCM、欧拉定理、中国剩余定理等核心工具。' },
  { id:'big-integer',     name:'高精度',         nameEn:'Big Integer',            category:'数学',     difficulty:'提高', desc:'用数组模拟任意精度整数的四则运算，处理超出 long long 范围的计算问题。' },
  { id:'bitwise',         name:'位运算',         nameEn:'Bit Manipulation',       category:'数学',     difficulty:'提高', desc:'用二进制位操作加速计算，常用于状态压缩、快速奇偶判断、子集枚举等场景。' },
  { id:'combinatorics',   name:'组合数学',       nameEn:'Combinatorics',          category:'数学',     difficulty:'进阶', desc:'排列组合、卡特兰数、容斥原理、Burnside 引理等计数工具，是数学竞赛核心。' },
  { id:'matrix',          name:'矩阵',           nameEn:'Matrix',                 category:'数学',     difficulty:'进阶', desc:'矩阵快速幂将线性递推第 n 项求解降至 O(k³ log n)，也用于图上路径计数。' },
  { id:'geometry',        name:'几何',           nameEn:'Computational Geometry', category:'数学',     difficulty:'进阶', desc:'凸包、点线面关系、旋转卡壳等，叉积是判断方向的核心工具，需仔细处理精度。' },
  { id:'game-theory',     name:'博弈论',         nameEn:'Game Theory',            category:'数学',     difficulty:'进阶', desc:'Nim 游戏、SG 函数分析先手必胜/必败，Sprague-Grundy 定理是组合博弈的核心。' },
  { id:'probability',     name:'概率',           nameEn:'Probability',            category:'数学',     difficulty:'进阶', desc:'期望 DP、随机算法等，常求解随机过程的期望步数或特定事件的发生概率。' },
]

const DETAIL = {
  'bubble-sort': {
    description: '冒泡排序通过多轮遍历数组，每次比较相邻元素并交换逆序对，最大元素不断"冒泡"至末尾。配合无交换标志优化，最佳情况可达 O(n)。虽然实际性能不如快排，但逻辑简单，是学习排序的起点。',
    steps: ['外层循环控制遍历轮数（共 n-1 轮）','内层循环从头遍历到未排序部分末尾','若相邻两元素逆序则交换，并标记 swapped=true','本轮结束若 swapped 为 false，数组已有序，提前退出','每轮至少一个最大元素沉到正确位置'],
    complexity: [{ case:'最好（已有序）', time:'O(n)', space:'O(1)' },{ case:'平均', time:'O(n²)', space:'O(1)' },{ case:'最坏（逆序）', time:'O(n²)', space:'O(1)' }],
    stable: true,
    codes: {
      'C++': `#include <bits/stdc++.h>
using namespace std;
void bubbleSort(vector<int>& arr) {
    int n = arr.size();
    for (int i = 0; i < n - 1; i++) {
        bool swapped = false;
        for (int j = 0; j < n - 1 - i; j++) {
            if (arr[j] > arr[j + 1]) {
                swap(arr[j], arr[j + 1]);
                swapped = true;
            }
        }
        if (!swapped) break;
    }
}`,
      Java: `public class BubbleSort {
    public static void sort(int[] arr) {
        int n = arr.length;
        for (int i = 0; i < n - 1; i++) {
            boolean swapped = false;
            for (int j = 0; j < n - 1 - i; j++) {
                if (arr[j] > arr[j + 1]) {
                    int tmp = arr[j]; arr[j] = arr[j+1]; arr[j+1] = tmp;
                    swapped = true;
                }
            }
            if (!swapped) break;
        }
    }
}`,
      Python: `def bubble_sort(arr):
    n = len(arr)
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break`,
    },
  },
  'binary-search': {
    description: '二分查找在有序序列中每次将区间折半，用 O(log n) 时间定位目标。二分答案是其重要扩展：若答案具有单调性（满足/不满足），可对答案空间二分，将枚举优化为对数级。',
    steps: ['确定查找区间 [l, r]（通常为 [0, n-1]）','取中点 mid = l + (r-l)/2，避免溢出','若 arr[mid] == target，返回 mid','若 arr[mid] < target，目标在右半段，l = mid + 1','否则目标在左半段，r = mid - 1','循环直到 l > r，说明不存在'],
    complexity: [{ case:'所有情况', time:'O(log n)', space:'O(1)' }],
    stable: true,
    codes: {
      'C++': `#include <bits/stdc++.h>
using namespace std;
int binarySearch(vector<int>& arr, int target) {
    int l = 0, r = arr.size() - 1;
    while (l <= r) {
        int mid = l + (r - l) / 2;
        if (arr[mid] == target) return mid;
        else if (arr[mid] < target) l = mid + 1;
        else r = mid - 1;
    }
    return -1;
}`,
      Java: `public static int binarySearch(int[] arr, int target) {
    int l = 0, r = arr.length - 1;
    while (l <= r) {
        int mid = l + (r - l) / 2;
        if (arr[mid] == target) return mid;
        else if (arr[mid] < target) l = mid + 1;
        else r = mid - 1;
    }
    return -1;
}`,
      Python: `def binary_search(arr, target):
    l, r = 0, len(arr) - 1
    while l <= r:
        mid = (l + r) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            l = mid + 1
        else:
            r = mid - 1
    return -1`,
    },
  },
  'union-find': {
    description: '并查集（DSU）用于高效维护元素的分组信息，支持合并两个集合与查询两元素是否同组。路径压缩让 find() 沿途节点直接指向根；按秩合并让小树挂在大树下——两者结合使得单次操作均摊近似 O(1)（准确为反阿克曼函数）。',
    steps: ['初始化：每个元素的父节点指向自身，秩为 0','find(x)：递归找根，路径压缩使沿途节点直接指向根','union(x, y)：找到两者的根，若不同则按秩合并（秩小挂在秩大下面）','判断连通：find(x) == find(y)'],
    complexity: [{ case:'单次操作（均摊）', time:'O(α(n)) ≈ O(1)', space:'O(n)' }],
    stable: true,
    codes: {
      'C++': `#include <bits/stdc++.h>
using namespace std;
struct DSU {
    vector<int> parent, rank_;
    DSU(int n) : parent(n), rank_(n, 0) {
        iota(parent.begin(), parent.end(), 0);
    }
    int find(int x) {
        if (parent[x] != x) parent[x] = find(parent[x]);
        return parent[x];
    }
    bool unite(int x, int y) {
        x = find(x); y = find(y);
        if (x == y) return false;
        if (rank_[x] < rank_[y]) swap(x, y);
        parent[y] = x;
        if (rank_[x] == rank_[y]) rank_[x]++;
        return true;
    }
    bool connected(int x, int y) { return find(x) == find(y); }
};`,
      Java: `class DSU {
    int[] parent, rank;
    DSU(int n) {
        parent = new int[n]; rank = new int[n];
        for (int i = 0; i < n; i++) parent[i] = i;
    }
    int find(int x) {
        if (parent[x] != x) parent[x] = find(parent[x]);
        return parent[x];
    }
    boolean unite(int x, int y) {
        x = find(x); y = find(y);
        if (x == y) return false;
        if (rank[x] < rank[y]) { int t = x; x = y; y = t; }
        parent[y] = x;
        if (rank[x] == rank[y]) rank[x]++;
        return true;
    }
}`,
      Python: `class DSU:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    def unite(self, x, y):
        x, y = self.find(x), self.find(y)
        if x == y: return False
        if self.rank[x] < self.rank[y]: x, y = y, x
        self.parent[y] = x
        if self.rank[x] == self.rank[y]: self.rank[x] += 1
        return True`,
    },
  },
}

// ── 状态 ─────────────────────────────────────────────────────
const keyword = ref('')
const activeCategory = ref('全部')
const detail = ref(null)
const codeLang = ref('C++')
const CODE_LANGS = ['C++', 'Java', 'Python']

function diffClass(d) {
  if (d === '入门') return 'diff-beginner'
  if (d === '提高') return 'diff-intermediate'
  return 'diff-advanced'
}

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return ALGORITHMS.filter(a => {
    const catOk = activeCategory.value === '全部' || a.category === activeCategory.value
    const kwOk = !kw || a.name.toLowerCase().includes(kw) || a.nameEn.toLowerCase().includes(kw)
    return catOk && kwOk
  })
})

function openDetail(algo) {
  detail.value = { algo, data: DETAIL[algo.id] || null }
  codeLang.value = 'C++'
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
function closeDetail() { detail.value = null }

// ── 视差 Hero ────────────────────────────────────────────────
const heroRef = ref(null)
let onScroll = null
onMounted(() => {
  onScroll = () => {
    if (!heroRef.value) return
    const el = heroRef.value.querySelector('.hero-parallax-bg')
    if (el) el.style.transform = `translateY(${window.scrollY * 0.3}px)`
  }
  window.addEventListener('scroll', onScroll, { passive: true })
})
onUnmounted(() => { if (onScroll) window.removeEventListener('scroll', onScroll) })
</script>

<template>
  <div class="learn-page">

    <!-- ===== 详情视图 ===== -->
    <div v-if="detail" class="view-detail">
      <div class="breadcrumb">
        <span class="bc-link" @click="closeDetail">算法学习</span>
        <span class="bc-sep">/</span>
        <span class="bc-cur">{{ detail.algo.name }}</span>
      </div>

      <div class="detail-header">
        <div class="detail-title">{{ detail.algo.name }}</div>
        <div class="detail-title-en">{{ detail.algo.nameEn }}</div>
        <div class="detail-meta">
          <span class="diff-learn" :class="diffClass(detail.algo.difficulty)">{{ detail.algo.difficulty }}</span>
          <span class="cat-pill">{{ detail.algo.category }}</span>
        </div>
      </div>

      <template v-if="detail.data">
        <!-- 简介 -->
        <div class="detail-section">
          <div class="section-hd">算法简介</div>
          <p class="detail-text">{{ detail.data.description }}</p>
        </div>

        <!-- 步骤 -->
        <div class="detail-section" v-if="detail.data.steps">
          <div class="section-hd">执行步骤</div>
          <ol class="steps-list">
            <li v-for="s in detail.data.steps" :key="s">{{ s }}</li>
          </ol>
        </div>

        <!-- 复杂度 -->
        <div class="detail-section" v-if="detail.data.complexity">
          <div class="section-hd">时空复杂度</div>
          <table class="complexity-table">
            <thead><tr><th>情况</th><th>时间复杂度</th><th>空间复杂度</th></tr></thead>
            <tbody>
              <tr v-for="r in detail.data.complexity" :key="r.case">
                <td>{{ r.case }}</td><td>{{ r.time }}</td><td>{{ r.space }}</td>
              </tr>
            </tbody>
          </table>
          <div class="stable-tag" v-if="detail.data.stable !== undefined">
            {{ detail.data.stable ? '✓ 稳定排序' : '✗ 不稳定排序' }}
          </div>
        </div>

        <!-- 代码 -->
        <div class="detail-section" v-if="detail.data.codes">
          <div class="section-hd">参考代码</div>
          <div class="code-tabs">
            <div class="code-tab-bar">
              <button
                v-for="lang in CODE_LANGS" :key="lang"
                class="code-tab" :class="{ active: codeLang === lang }"
                @click="codeLang = lang"
              >{{ lang }}</button>
            </div>
            <div class="code-body" v-if="detail.data.codes[codeLang]">
              <pre><code>{{ detail.data.codes[codeLang] }}</code></pre>
            </div>
            <div class="code-empty" v-else>暂无该语言的参考代码</div>
          </div>
        </div>
      </template>

      <!-- 无详情数据时 -->
      <div class="no-detail" v-else>
        <div class="nd-icon">📝</div>
        <p>该算法的详细内容正在整理中，敬请期待</p>
        <p class="nd-desc">{{ detail.algo.desc }}</p>
      </div>
    </div>

    <!-- ===== 列表视图 ===== -->
    <div v-else>

      <!-- Hero -->
      <div class="learn-hero" ref="heroRef">
        <div class="hero-parallax-bg">
          <div class="hero-grad"></div>
          <svg class="deco-hex" style="left:-4%;top:-30%;width:50%;" viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg">
            <defs><pattern id="hexA" x="0" y="0" width="52" height="60" patternUnits="userSpaceOnUse"><polygon points="26,2 50,15 50,45 26,58 2,45 2,15" fill="none" stroke="#7c6af7" stroke-width="1.2"/></pattern></defs>
            <rect width="400" height="400" fill="url(#hexA)"/>
          </svg>
          <svg class="deco-hex" style="right:-6%;bottom:-40%;width:42%;opacity:0.05;" viewBox="0 0 300 300" xmlns="http://www.w3.org/2000/svg">
            <defs><pattern id="hexB" x="0" y="0" width="52" height="60" patternUnits="userSpaceOnUse"><polygon points="26,2 50,15 50,45 26,58 2,45 2,15" fill="none" stroke="#22d3ee" stroke-width="1.2"/></pattern></defs>
            <rect width="300" height="300" fill="url(#hexB)"/>
          </svg>
          <span class="code-float" style="left:7%;top:22%">O(n log n)</span>
          <span class="code-float" style="right:14%;top:28%">dp[i][j] = dp[i-1][j-1] + 1</span>
          <span class="code-float" style="left:22%;bottom:26%">BFS / DFS</span>
          <span class="code-float" style="right:9%;bottom:32%">while (l &lt;= r)</span>
          <span class="code-float" style="left:48%;top:18%">Dijkstra</span>
        </div>
        <div class="hero-content">
          <h1 class="learn-hero-title">算法学习</h1>
          <p class="learn-hero-sub">从原理到实战，系统掌握每一个算法<br>边学习、边刷题，稳步提升竞赛实力</p>
        </div>
      </div>

      <!-- 控制区 -->
      <div class="learn-controls">
        <div class="search-row">
          <div class="search-wrapper">
            <svg class="search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input v-model="keyword" class="search-input" placeholder="搜索算法名称…" />
          </div>
        </div>
        <div class="category-bar">
          <span
            v-for="cat in CATEGORIES" :key="cat"
            class="cat-tag" :class="{ active: activeCategory === cat }"
            @click="activeCategory = cat"
          >{{ cat }}</span>
        </div>
      </div>

      <!-- 卡片网格 -->
      <div class="algo-section">
        <div class="algo-grid">
          <div
            v-for="algo in filtered" :key="algo.id"
            class="algo-card"
            @click="openDetail(algo)"
          >
            <div class="algo-card-header">
              <div>
                <div class="algo-name">{{ algo.name }}</div>
                <div class="algo-name-en">{{ algo.nameEn }}</div>
              </div>
              <span class="diff-learn" :class="diffClass(algo.difficulty)">{{ algo.difficulty }}</span>
            </div>
            <p class="algo-desc">{{ algo.desc }}</p>
            <div class="algo-footer">
              <span class="algo-category-tag">{{ algo.category }}</span>
              <svg class="algo-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 18l6-6-6-6"/></svg>
            </div>
          </div>
        </div>
        <div v-if="filtered.length === 0" class="learn-empty">
          <div class="learn-empty-icon">🔍</div>
          <p>没有找到匹配的算法</p>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.learn-page { padding: 0; }

/* ── Hero ─────────────────────────────────── */
.learn-hero {
  position: relative; height: 300px; overflow: hidden;
  display: flex; align-items: center; justify-content: center; text-align: center;
  margin-bottom: 0;
}
.learn-hero::after {
  content: ''; position: absolute; bottom: -1px; left: 0; right: 0; height: 100px;
  background: linear-gradient(to bottom, transparent, var(--bg-primary));
  z-index: 3; pointer-events: none;
}
.hero-parallax-bg {
  position: absolute; inset: -80px 0 0 0; pointer-events: none; overflow: hidden;
}
.hero-grad {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(124,106,247,0.14) 0%, rgba(34,211,238,0.07) 50%, transparent 100%);
}
.deco-hex { position: absolute; opacity: 0.07; }
.code-float {
  position: absolute; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
  color: #7c6af7; opacity: 0.22; white-space: nowrap;
  animation: floatY 7s ease-in-out infinite;
}
.code-float:nth-child(2) { animation-delay: -2.5s; animation-duration: 9s; }
.code-float:nth-child(3) { animation-delay: -5s;   animation-duration: 6.5s; }
.code-float:nth-child(4) { animation-delay: -1s;   animation-duration: 8.5s; }
.code-float:nth-child(5) { animation-delay: -3.5s; animation-duration: 7.5s; }
@keyframes floatY { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-14px)} }

.hero-content { position: relative; z-index: 2; padding: 0 24px; }
.learn-hero-title {
  font-size: 2.8rem; font-weight: 800;
  background: linear-gradient(135deg, #7c6af7 0%, #22d3ee 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
  margin-bottom: 10px;
}
.learn-hero-sub { color: var(--text-muted); font-size: 1rem; line-height: 1.7; margin: 0; }

/* ── 控制区 ─────────────────────────────────── */
.learn-controls {
  position: sticky; top: 56px; z-index: 50;
  background: var(--bg-primary); padding: 12px 0 10px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 1.5rem;
}
.search-row { margin-bottom: 8px; }
.search-wrapper { position: relative; max-width: 360px; }
.search-icon { position: absolute; left: 11px; top: 50%; transform: translateY(-50%); color: var(--text-muted); pointer-events: none; }
.search-input {
  width: 100%; padding: 8px 14px 8px 36px;
  background: var(--bg-input); color: var(--text-primary);
  border: 1px solid var(--border); border-radius: 8px;
  font-size: 0.88rem; outline: none; transition: border-color 0.15s;
}
.search-input:focus { border-color: var(--accent); }

.category-bar { display: flex; gap: 8px; overflow-x: auto; scrollbar-width: none; padding: 2px 0 4px; }
.category-bar::-webkit-scrollbar { display: none; }
.cat-tag {
  flex-shrink: 0; padding: 5px 16px; border-radius: 20px;
  border: 1px solid var(--border); background: var(--bg-card);
  color: var(--text-muted); font-size: 0.83rem; font-weight: 500;
  cursor: pointer; transition: all 0.15s; white-space: nowrap;
}
.cat-tag:hover  { border-color: var(--accent); color: var(--accent); }
.cat-tag.active { border-color: var(--accent); color: var(--accent); background: rgba(124,106,247,0.12); font-weight: 600; }

/* ── 卡片网格 ────────────────────────────────── */
.algo-section { padding: 0 0 4rem; }
.algo-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px;
}
.algo-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 10px; padding: 18px 20px;
  cursor: pointer; position: relative; overflow: hidden;
  transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s;
}
.algo-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, #7c6af7, #22d3ee);
  transform: scaleX(0); transform-origin: left; transition: transform 0.3s;
}
.algo-card:hover { border-color: var(--accent); transform: translateY(-3px); box-shadow: 0 8px 24px rgba(124,106,247,0.15); }
.algo-card:hover::before { transform: scaleX(1); }

.algo-card-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
.algo-name    { font-size: 0.97rem; font-weight: 600; color: var(--text-primary); }
.algo-name-en { font-size: 0.72rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; margin-top: 2px; }
.algo-desc    { font-size: 0.82rem; color: var(--text-muted); line-height: 1.55; margin: 6px 0 10px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.algo-footer  { display: flex; align-items: center; justify-content: space-between; }
.algo-category-tag { font-size: 0.72rem; color: var(--text-muted); padding: 2px 7px; background: var(--bg-input); border-radius: 4px; }
.algo-arrow   { color: var(--text-muted); }

.diff-learn { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; white-space: nowrap; }
.diff-beginner    { background: rgba(34,197,94,0.12);  color: #22c55e; }
.diff-intermediate{ background: rgba(251,191,36,0.12); color: #f59e0b; }
.diff-advanced    { background: rgba(239,68,68,0.12);  color: #ef4444; }

.learn-empty { text-align: center; padding: 4rem; color: var(--text-muted); }
.learn-empty-icon { font-size: 2.5rem; margin-bottom: 10px; opacity: 0.4; }

/* ── 详情视图 ────────────────────────────────── */
.view-detail { max-width: 860px; }

.breadcrumb { display: flex; align-items: center; gap: 8px; font-size: 0.87rem; margin-bottom: 1.5rem; }
.bc-link { color: var(--accent); cursor: pointer; }
.bc-link:hover { text-decoration: underline; }
.bc-sep { color: var(--border); }
.bc-cur { color: var(--text-primary); font-weight: 500; }

.detail-header { margin-bottom: 2rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--border); }
.detail-title    { font-size: 2rem; font-weight: 800; color: var(--text-primary); margin-bottom: 4px; }
.detail-title-en { font-family: 'JetBrains Mono', monospace; font-size: 0.95rem; color: var(--text-muted); margin-bottom: 12px; }
.detail-meta     { display: flex; align-items: center; gap: 10px; }
.cat-pill { font-size: 0.8rem; color: var(--text-muted); padding: 3px 10px; background: var(--bg-input); border-radius: 6px; }

.detail-section { margin-bottom: 2rem; }
.section-hd {
  font-size: 1rem; font-weight: 700; color: var(--text-primary);
  margin-bottom: 12px; padding-left: 10px;
  border-left: 3px solid var(--accent);
}
.detail-text { color: var(--text-secondary); line-height: 1.8; font-size: 0.92rem; margin: 0; }

.steps-list { list-style: none; counter-reset: step-counter; padding: 0; display: flex; flex-direction: column; gap: 6px; margin: 0; }
.steps-list li {
  counter-increment: step-counter;
  display: flex; align-items: flex-start; gap: 12px;
  padding: 10px 14px; background: var(--bg-input);
  border-radius: 8px; font-size: 0.88rem; color: var(--text-secondary);
}
.steps-list li::before {
  content: counter(step-counter);
  min-width: 22px; height: 22px;
  background: linear-gradient(135deg, var(--accent), #22d3ee);
  color: #fff; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 0.72rem; font-weight: 700; flex-shrink: 0; margin-top: 1px;
}

.complexity-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
.complexity-table th { padding: 10px 14px; text-align: left; background: var(--bg-input); color: var(--text-secondary); font-weight: 600; border-bottom: 1px solid var(--border); }
.complexity-table td { padding: 10px 14px; border-bottom: 1px solid var(--border); color: var(--text-primary); }
.complexity-table td:not(:first-child) { font-family: 'JetBrains Mono', monospace; color: var(--accent); }
.complexity-table tr:last-child td { border-bottom: none; }
.stable-tag { margin-top: 8px; font-size: 0.82rem; color: var(--text-muted); }

.code-tabs { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.code-tab-bar { display: flex; border-bottom: 1px solid var(--border); background: var(--bg-input); }
.code-tab {
  padding: 8px 18px; background: none; border: none; border-bottom: 2px solid transparent;
  color: var(--text-muted); font-size: 0.85rem; cursor: pointer; transition: all 0.15s;
  margin-bottom: -1px;
}
.code-tab:hover { color: var(--text-primary); }
.code-tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.code-body pre {
  margin: 0; padding: 1.2rem 1.4rem;
  background: #12121e; overflow-x: auto; max-height: 480px;
}
.code-body code { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.85rem; color: #c8d0e0; line-height: 1.65; }
.code-empty { padding: 1.5rem; text-align: center; color: var(--text-muted); font-size: 0.88rem; }

.no-detail { text-align: center; padding: 3rem 1rem; }
.nd-icon { font-size: 3rem; margin-bottom: 1rem; }
.no-detail p { color: var(--text-muted); margin: 0.5rem 0; }
.nd-desc { font-size: 0.88rem; max-width: 480px; margin: 0.5rem auto 0; line-height: 1.7; }

@media (max-width: 1100px) { .algo-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 768px)  { .algo-grid { grid-template-columns: repeat(2, 1fr); } .learn-hero-title { font-size: 2rem; } }
@media (max-width: 480px)  { .algo-grid { grid-template-columns: 1fr; } }
</style>
