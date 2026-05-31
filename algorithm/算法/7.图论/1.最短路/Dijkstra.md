#难度/★★★

> 贪心 + 优先队列，每次"确定一个距起点最近的节点"再去松弛它的邻居，求**非负权图**的单源最短路。

## 前置知识

- [[堆]]

- [[BFS]]

## 核心思想

Dijkstra 求**单源最短路**——给定起点 $s$，求 $s$ 到图中所有点的最短距离。它的核心是一个**贪心策略**：

把所有节点分为两个集合：

- $S$：已确定最短路的节点

- $V \setminus S$：未确定的节点

**关键观察**：在 $V \setminus S$ 中找出当前 `dist` 值**最小**的节点 $u$，则 `dist[u]` 已经是 $s \to u$ 的真实最短路——再无更短路径可能。证明依赖于"边权非负"：任何经过 $V \setminus S$ 中其他节点再回到 $u$ 的路径，长度只会更大。

于是算法流程为：

1. 从 $V \setminus S$ 中取出 `dist` 最小的节点 $u$，加入 $S$

2. 用 $u$ 去**松弛**它的每个邻居 $v$：若 `dist[u] + w(u,v) < dist[v]`，则更新 `dist[v]`

3. 重复直到 $V \setminus S$ 为空

朴素实现每次扫描数组找最小值，$O(n^2)$。用 **优先队列**（最小堆）维护 $V \setminus S$ 的 `dist`，把"取最小"降到 $O(\log n)$，得到主流的 $O((n + m) \log n)$ 堆优化版。

与 [[BFS]] 的关系：BFS 是"边权全为 1 的 Dijkstra"——用普通队列就够了，因为按层扩展自然就是按距离扩展。Dijkstra 推广到任意非负权时，必须改用优先队列才能"按距离最小优先"。

## 适用场景

- **单源最短路**且边权非负（最经典应用）

- 稀疏图：堆优化版 $O((n + m) \log n)$ 是首选

- 稠密图（$m \approx n^2$）：朴素 $O(n^2)$ Dijkstra 反而更优

- 经典扩展：求次短路、$k$ 短路（配合 [[A∗]]）、动态加点

- 不适用：存在负权边（用 [[SPFA]]）；只关心步数（用 [[BFS]]，常数更小）；所有点对最短路（小图用 [[Floyd]]，大图跑 $n$ 次 Dijkstra）

## 步骤拆解

1. 初始化 `dist[s] = 0`，其他节点 `dist[] = +∞`

2. 把 $(0, s)$ 压入小根堆

3. 循环直到堆空：

   a. 取出堆顶 $(d, u)$

   b. **若 $d > \mathtt{dist}[u]$，跳过**（这是过期记录，详见下方说明）

   c. 否则枚举 $u$ 的每条出边 $(u, v, w)$：若 `dist[u] + w < dist[v]`，更新 `dist[v]` 并把 $(\mathtt{dist}[v], v)$ 压入堆

## 代码模板

**堆优化版：

```cpp

class dijkstra {

private:

    int n;

    vector<vector<pair<int, long long>>> g;     // g[u] = {邻居, 边权}

public:

    dijkstra(int total, vector<vector<pair<int, long long>>>& g_in) {

        n = total;

        g = g_in;

    }

    vector<long long> shortest_path(int start) {

        const long long INF = 1e18;

        vector<long long> dist(n + 1, INF);

        priority_queue<

            pair<long long, int>,

            vector<pair<long long, int>>,

            greater<pair<long long, int>>

        > pq;

        dist[start] = 0;

        pq.push({0, start});

  

        while (!pq.empty()) {

            auto [d, u] = pq.top();

            pq.pop();

            if (d > dist[u]) {                  // 过期项，跳过

                continue;

            }

            for (auto [v, w] : g[u]) {

                if (dist[u] + w < dist[v]) {

                    dist[v] = dist[u] + w;

                    pq.push({dist[v], v});

                }

            }

        }

        return dist;

    }

};
```

> 💡 **关于"过期项"**：当 $\mathtt{dist}[v]$ 被更新时，我们把 $(\mathtt{dist}[v], v)$ 压入堆，但**不删除**堆中已存在的 $v$ 旧记录（堆不支持 $O(\log n)$ 删除任意元素）。后续取出旧记录时，它的 $d$ 值大于当前 $\mathtt{dist}[v]$，直接跳过即可。每条边最多产生一个堆条目，总复杂度仍是 $O(m \log m)$。

**朴素版（稠密图首选）**：

```cpp

class dijkstra_dense {

private:

    int n;

    vector<vector<long long>> w;                // 邻接矩阵，无边为 INF

public:

    dijkstra_dense(int total, vector<vector<long long>>& w_in) {

        n = total;

        w = w_in;

    }

    vector<long long> shortest_path(int start) {

        const long long INF = 1e18;

        vector<long long> dist(n + 1, INF);

        vector<bool> visited(n + 1, false);

        dist[start] = 0;

        for (int iter = 1; iter <= n; iter++) {

            // 1. 找出未访问中 dist 最小的节点
            int u = 0;

            long long min_d = INF;

            for (int i = 1; i <= n; i++) {

                if (!visited[i] && dist[i] < min_d) {

                    min_d = dist[i];

                    u = i;

                }

            }

            if (u == 0) {

                break;                          // 剩余节点不可达

            }

            visited[u] = true;

            // 2. 松弛 u 的邻居
            for (int v = 1; v <= n; v++) {

                if (!visited[v] && w[u][v] != INF) {

                    if (dist[u] + w[u][v] < dist[v]) {

                        dist[v] = dist[u] + w[u][v];

                    }

                }

            }

        }

        return dist;

    }

};
```

> 💡 **何时用朴素版**：当 $m \approx n^2$（稠密图）时，堆版 $O(m \log n) = O(n^2 \log n)$ 反而比朴素 $O(n^2)$ 慢。此外朴素版常数小、代码无堆相关的过期判断，更稳定。

**还原最短路径**：在松弛 $\mathtt{dist}[v]$ 时记下 `parent[v] = u`，最后从终点沿 `parent` 回溯到起点即可。

## 复杂度分析

- 时间复杂度：

  - 堆优化版：$O((n + m) \log n)$

  - 朴素版：$O(n^2)$

- 空间复杂度：$O(n + m)$

## 正确性证明

### 关键不变量：取出即最优

**核心定理**：每当节点 $u$ 从堆中取出且**未过期**（即 $d = \mathtt{dist}[u]$）时，$\mathtt{dist}[u]$ 已经是 $s \to u$ 的真实最短路。

**证明（反证 + 归纳）**：

设 $u$ 是算法运行中**第一个被错误确认**的节点——即取出 $u$ 时 $\mathtt{dist}[u] > d^*$，其中 $d^*$ 是 $s \to u$ 的真实最短路。由"第一个错误"的假设，所有此前已确认的节点 `dist` 都正确。

由 $d^*$ 为真实最短路，存在路径

$$P:\; s = v_0 \to v_1 \to \cdots \to v_k = u, \quad |P| = d^*$$

设 $v_i$ 是 $P$ 上**第一个尚未被确认**的节点（$v_i$ 必然存在：$v_k = u$ 还没被确认；且 $v_0 = s$ 在算法第一步就被确认，所以 $i \ge 1$）。

考察 $v_{i-1}$：由"$u$ 是第一个错误确认的"假设，$\mathtt{dist}[v_{i-1}] =$ $s \to v_{i-1}$ 的真实最短路。由于 $v_{i-1}$ 已确认，它已经松弛过 $v_i$，所以

$$\mathtt{dist}[v_i] \le \mathtt{dist}[v_{i-1}] + w(v_{i-1}, v_i) = (P \text{ 上 } s \to v_i \text{ 的长度})$$

由 $P$ 上从 $v_i$ 到 $u$ 的所有边权**非负**，

$$(P \text{ 上 } s \to v_i \text{ 的长度}) \le |P| = d^* < \mathtt{dist}[u]$$

合并得 $\mathtt{dist}[v_i] < \mathtt{dist}[u]$。但 $v_i$ 此刻在堆中，$u$ 也在堆中——按算法应优先取出 $\mathtt{dist}$ 更小的 $v_i$，与"$u$ 被取出"矛盾。$\blacksquare$

### 边权非负的必要性

上述证明的关键步骤是"$P$ 上从 $v_i$ 到 $u$ 的边权和非负，所以 $s \to v_i$ 子路径不长于全程 $d^*$"。

若存在负权边，子路径加上后续负边可能反而更短——证明链条断裂。

**反例**：三角形 $s \to a$ 边权 $1$，$s \to b$ 边权 $2$，$b \to a$ 边权 $-2$。

Dijkstra 先确认 $a$（$\mathtt{dist}[a] = 1$），但真实最短路是 $s \to b \to a$ 长度为 $0$。算法已经把 $a$ 加入 $S$ 不再更新，错失更短路径。

所以 Dijkstra 严格依赖**边权非负**。含负权时必须用 [[SPFA]] 或 Bellman-Ford。

### 过期项跳过的合法性

**命题**：当从堆中取出 $(d, u)$ 而 $d > \mathtt{dist}[u]$ 时，直接跳过不影响正确性。

**证明**：$\mathtt{dist}[u] < d$ 意味着 $u$ 后来又被更短的路径松弛过——那次松弛已经把新的 $(\mathtt{dist}[u], u)$ 压入堆。当前这个 $(d, u)$ 是**已被超越的旧记录**。

若不跳过会怎样？继续用 $d$ 去松弛 $u$ 的邻居 $v$：判断 `dist[u] + w < dist[v]` 时使用的是当前正确的 $\mathtt{dist}[u]$（不是 $d$），所以不会得出错误结论，但会做无谓的边检查。跳过只是优化常数，不改变正确性。$\blacksquare$

### 复杂度的来源

每条边 $(u, v)$ 最多在 $u$ 被某次松弛后产生一次堆压入操作。总堆条目数为 $O(m)$，每次 push / pop 是 $O(\log m) = O(\log n)$。再加上初始化的 $O(n)$ 工作，总复杂度 $O((n + m) \log n)$。$\blacksquare$

## 与相关算法的对比

| 维度         | Dijkstra（堆）         | [[BFS]]       | [[SPFA]]               | [[Floyd]]     |
| ---------- | ------------------- | ------------- | ---------------------- | ------------- |
| 边权要求       | 非负                  | 全为 1          | 任意（无负环）                | 任意（无负环）       |
| 用途         | 单源                  | 单源            | 单源                     | 全源            |
| 复杂度        | $O((n+m) \log n)$   | $O(n + m)$    | 平均 $O(km)$，最坏 $O(nm)$  | $O(n^3)$      |
| 实战稳定性      | 极稳定                 | 极稳定           | 易被卡                    | 极稳定           |


**经验**：边权全 0/1 用 [[0-1 BFS]]；边权全 1 用 [[BFS]]；边权非负用 Dijkstra；含负权才考虑 [[SPFA]]。

## 相关例题

- [洛谷P4779 【模板】单源最短路径（标准版）](https://www.luogu.com.cn/problem/P4779)

- [洛谷P3371 【模板】单源最短路径（弱化版）](https://www.luogu.com.cn/problem/P3371