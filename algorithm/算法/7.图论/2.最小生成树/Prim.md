#难度/★★★

> 从某点出发维护"已选连通块"，每次把它到外界的最小代价边加入——MST 版的 [[Dijkstra]]。

## 前置知识

- [[堆]]

- [[Dijkstra]]

## 核心思想

Prim 也是构造**最小生成树**的算法，但与 [[Kruskal]] 的"全局贪心扫边"不同——Prim 是**局部贪心**：维护一个不断扩展的连通块 $S$（初始只含一个起点），每次把 $S$ 到外界的**最便宜的横跨边**加入 MST，让 $S$ 多吸收一个新节点。

具体地，对每个尚未加入 $S$ 的节点 $v$，维护

$$\mathtt{dist}[v] = \min_{u \in S,\, (u,v) \in E} w(u, v)$$

即 $v$ 到当前 $S$ 的"最便宜入门票"。算法每次取 $\mathtt{dist}$ 最小的 $v$ 加入 $S$，并用 $v$ 的邻居更新它们的 $\mathtt{dist}$。

**与 [[Dijkstra]] 的对比**：两者结构几乎一致——区别只在 $\mathtt{dist}$ 的语义。Dijkstra 中 $\mathtt{dist}[v]$ 是"从起点到 $v$ 的最短路"，松弛公式为 $\mathtt{dist}[u] + w$；Prim 中 $\mathtt{dist}[v]$ 是"$v$ 到 $S$ 的最短入门票"，松弛公式直接是 $w$（边权本身）。算法骨架（堆优化、过期项、循环 $n$ 次）完全一致。

正确性同样依赖**割性质**——每次 $S$ 把图切成 $(S, V \setminus S)$，Prim 选的就是这个割上的最小横跨边，所以这条边必在某棵 MST 中。

## 适用场景

- 求最小生成树

- **稠密图**（$m \approx n^2$）首选：朴素 $O(n^2)$ Prim 比 Kruskal 的 $O(m \log m) = O(n^2 \log n)$ 更优

- 经典扩展：求最小斯坦纳树时作为一部分；网络流前置的某些图缩减

- 不适用：稀疏图（用 [[Kruskal]] 更短更快）；多个连通块（Prim 一次只处理起点所在的连通块，需多次启动）

## 步骤拆解

1. 任选起点 $s$（通常取 1 号节点）；初始化 `dist[s] = 0`，其他为 $+\infty$

2. 循环 $n$ 次：

   a. 选出未加入 $S$ 的节点中 `dist` 最小的 $u$

   b. 把 $u$ 加入 $S$，累加 `dist[u]` 到答案

   c. 枚举 $u$ 的每条出边 $(u, v, w)$：若 $v \notin S$ 且 $w < \mathtt{dist}[v]$，更新 `dist[v] = w`

3. 若某轮找不到可加入的节点（即剩余节点均不可达），图不连通

## 代码模板

**模板一：堆优化版（稀疏图）**：

```cpp

class prim {

private:

    int n;

    vector<vector<pair<int, long long>>> g;     // g[u] = {邻居, 边权}

public:

    prim(int total, vector<vector<pair<int, long long>>>& g_in) {

        n = total;

        g = g_in;

    }

    // 返回 MST 总权值；若图不连通返回 -1
    long long solve() {

        const long long INF = 1e18;

        vector<long long> dist(n + 1, INF);

        vector<bool> in_mst(n + 1, false);

        priority_queue<

            pair<long long, int>,

            vector<pair<long long, int>>,

            greater<pair<long long, int>>

        > pq;

        dist[1] = 0;

        pq.push({0, 1});

        long long total = 0;

        int cnt = 0;

        while (!pq.empty()) {

            auto [d, u] = pq.top();

            pq.pop();

            if (in_mst[u]) {                    // 过期或已加入

                continue;

            }

            in_mst[u] = true;

            total += d;

            cnt += 1;

            for (auto [v, w] : g[u]) {

                if (!in_mst[v] && w < dist[v]) {

                    dist[v] = w;

                    pq.push({w, v});

                }

            }

        }

        return cnt == n ? total : -1;

    }

};
```

> 💡 **过期项处理与 Dijkstra 一致**：用 `in_mst[]` 标记已加入的节点，从堆中取出后若已标记则跳过。每条边最多产生一次堆压入。

**模板二：朴素版（稠密图首选）**：

```cpp

class prim_dense {

private:

    int n;

    vector<vector<long long>> w;                // 邻接矩阵，无边为 INF

public:

    prim_dense(int total, vector<vector<long long>>& w_in) {

        n = total;

        w = w_in;

    }

    long long solve() {

        const long long INF = 1e18;

        vector<long long> dist(n + 1, INF);

        vector<bool> in_mst(n + 1, false);

        dist[1] = 0;

        long long total = 0;

        for (int iter = 1; iter <= n; iter++) {

            // 1. 找出未加入中 dist 最小的节点
            int u = 0;

            long long min_d = INF;

            for (int i = 1; i <= n; i++) {

                if (!in_mst[i] && dist[i] < min_d) {

                    min_d = dist[i];

                    u = i;

                }

            }

            if (u == 0) {

                return -1;                       // 图不连通

            }

            in_mst[u] = true;

            total += dist[u];

            // 2. 用 u 更新邻居的 dist
            for (int v = 1; v <= n; v++) {

                if (!in_mst[v] && w[u][v] < dist[v]) {

                    dist[v] = w[u][v];

                }

            }

        }

        return total;

    }

};
```

> 💡 **Prim 与 Dijkstra 代码的"几乎相同"**：唯一的差别是松弛行——Dijkstra 是 `dist[u] + w < dist[v]`（累加路径长度），Prim 是 `w < dist[v]`（只看入门票边权）。这种"算法骨架共享"是图论中常见的现象。

> ⚠️ **重边处理**：邻接矩阵存图时，对同一对节点取 `min` 保留最小边权。若用邻接表，重边不影响算法正确性（堆中可能有冗余但都会被过期跳过）。

## 复杂度分析

- 时间复杂度：

  - 朴素版：$O(n^2)$（适合稠密图）

  - 堆优化版：$O((n + m) \log n)$（适合稀疏图）

- 空间复杂度：

  - 朴素版：$O(n^2)$（邻接矩阵）

  - 堆优化版：$O(n + m)$（邻接表）

## 正确性证明

### 关键不变量

**核心不变量**：在 Prim 算法的任一时刻，已选边集 $T$ 都是某棵 MST 的子集。

### 主定理证明

**证明（归纳）**：以下用 $T_k$ 表示集合 $S$ 含 $k$ 个节点时已选边集（$T_1 = \emptyset$）。

**基础**：$T_1 = \emptyset$ 是任何 MST 的子集。

**归纳**：假设 $T_k$ 是某棵 MST $T^*$ 的子集，对应 $|S| = k$。考察第 $k + 1$ 步——算法加入 $u \notin S$，对应边 $e = (u', u)$，其中 $u' \in S$ 是使 $w(u', u) = \mathtt{dist}[u]$ 的某个邻居。

考虑割 $(S, V \setminus S)$：

- $e$ 横跨此割（$u' \in S, u \notin S$）。

- 由 $\mathtt{dist}[u]$ 的定义和算法选择 $u$ 为 $\mathtt{dist}$ 最小，$e$ 是当前所有 $S \to V \setminus S$ 横跨边中权值最小的。

由 [[Kruskal]] 笔记中证明的**割性质**：割 $(S, V \setminus S)$ 上的最小权横跨边 $e$ 必属于某棵 MST。

设 $T^{**}$ 为含 $e$ 的某棵 MST。我们要证 $T_{k+1} = T_k \cup \{e\}$ 也是某棵 MST 的子集——即可以让 $T^{**}$ 同时包含 $T_k$。

$T_k$ 中所有边都是 $S$ 内部的边（不横跨 $(S, V\setminus S)$，因为 $T_k$ 是 $S$ 的生成树边集，端点都在 $S$ 中）。在 $T^*$ 中 $T_k$ 出现，但 $e$ 可能不出现；在 $T^{**}$ 中 $e$ 出现，但 $T_k$ 中可能有边不出现。

**交换构造**：设 $T_k \setminus T^{**}$ 中某条边 $e_0$ 不在 $T^{**}$ 中。把 $e_0$ 加入 $T^{**}$ 形成唯一环 $C$。环 $C$ 上必有另一条边 $e_1$ 不在 $T_k$ 中（否则 $T_k$ 含环）。由 $T^{**}$ 是 MST，$w(e_1) \le w(e_0)$；由 $T^*$ 含 $T_k \cup \{e_0\}$ 但仍是 MST，$w(e_0) \le w(e_1)$。所以 $w(e_0) = w(e_1)$。

把 $T^{**}$ 中的 $e_1$ 替换为 $e_0$ 仍是 MST，且多含 $e_0$。重复此过程直到 $T^{**}$ 含 $T_k$ 中所有边。最终得到的 MST 同时含 $T_k$ 和 $e$，即 $T_{k+1}$ 是它的子集。

**终止**：当 $|S| = n$ 时已加入 $n - 1$ 条边，$T_{n}$ 是某棵 MST 的子集且边数为 $n - 1$——所以 $T_n$ 就是该 MST 本身。$\blacksquare$

### 与 [[Dijkstra]] 正确性的对比

Dijkstra 和 Prim 的算法骨架几乎一样——"维护一个数组 $\mathtt{dist}$，每次选最小，松弛邻居"——但它们的正确性证明走的是**不同路径**：

- Dijkstra：用反证 + 边权非负性证明"取出即最优"

- Prim：用归纳 + 割性质证明"已选边集始终是某棵 MST 的子集"

这种"相同骨架，不同性质"的现象很有趣。结构上的相似让两者都能 $O((n + m) \log n)$ 跑，但它们求的是完全不同的目标——单源路径 vs 全图连通。

### 复杂度的来源

**朴素版**：$n$ 轮主循环，每轮花 $O(n)$ 找最小 + $O(n)$ 松弛，总 $O(n^2)$。

**堆优化版**：每条边最多压入堆一次，堆操作 $O(\log n)$，总 $O((n + m) \log n)$。$\blacksquare$

## 与 [[Kruskal]] 的对比

| 维度        | Kruskal               | Prim 朴素            | Prim 堆优化           |
| --------- | --------------------- | ------------------ | ------------------ |
| 复杂度       | $O(m \log m)$         | $O(n^2)$           | $O((n+m) \log n)$  |
| 主导操作      | 边排序 + 并查集             | 数组扫描               | 堆操作                |
| 适合图密度     | 稀疏图                   | 稠密图                | 稀疏图                |
| 代码风格      | 全局视角（按权排边）            | 局部视角（连通块逐步扩展）      | 局部视角               |
| 多连通块处理    | 自然支持（结尾判边数）           | 需多次启动              | 需多次启动              |

**经验**：写起来 Kruskal 通常更快、更不易错。Prim 仅在 $m \approx n^2$ 时优势明显（朴素 Prim $O(n^2)$ 优于 Kruskal $O(n^2 \log n)$）。

## 相关例题

- [洛谷P3366 【模板】最小生成树](https://www.luogu.com.cn/problem/P3366)

- [洛谷P1546 [USACO3.1] 最短网络](https://www.luogu.com.cn/problem/P1546)

$\blacksquare$