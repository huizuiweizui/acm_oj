#难度/★★★

> 边权只有 0 和 1 时，用双端队列代替优先队列，实现 $O(n + m)$ 的最短路。

## 前置知识

- [[BFS]]

- [[队列]]

## 核心思想

普通 [[BFS]] 只能处理"边权全为 1"的最短路；[[Dijkstra]] 能处理任意非负边权但带个 $\log$。如果边权**只有 0 和 1**两种情况——这是一种很常见的特殊情形——可以用一个巧妙的"双端队列 BFS"在 $O(n + m)$ 内求出最短路。

**关键思想**：维护一个 `deque`，遵守一条规则——

- 走 0 边到达的节点，**插入队首**（`push_front`）

- 走 1 边到达的节点，**插入队尾**（`push_back`）

这样队列里的元素始终满足"从队首到队尾，距离单调不降"，等价于 [[Dijkstra]] 中优先队列的有序性，但每次入队 / 出队都是 $O(1)$ 而不是 $O(\log)$。

**为什么这样做对**：BFS 的正确性依赖"按距离层层扩展"；当所有边权为 1 时，自然按层扩展。当边权混合 0 和 1 时，0 边扩展不增加距离——所以新节点应该和当前节点同层（甚至更优先），用 `push_front` 让它们排在队首立即被处理。

## 适用场景

- 边权只有 0 / 1 的最短路问题（最经典应用）

- 网格图中"普通走 = 1，特殊通道 = 0"的混合场景

- 一些状态图问题：某些转移免费、某些转移收费

- 不适用：边权有 2 种以上的不同非负值（应用 [[Dijkstra]]）；存在负权（应用 [[SPFA]]）

## 步骤拆解

1. 初始化 `dist[]` 为 $+\infty$，`dist[start] = 0`

2. 起点 `push_front` 进 deque

3. 循环直到 deque 为空：

   a. 取出队首 $u$（`pop_front`）

   b. 若 `dist[u]` 已被更新过更小值（即出队时是过期版本），跳过

   c. 否则枚举每条边 $(u, v, w)$，若 `dist[u] + w < dist[v]`：

      - 更新 `dist[v]`

      - 若 $w = 0$，把 $v$ `push_front` 到队首

      - 若 $w = 1$，把 $v$ `push_back` 到队尾

## 代码模板

**模板：0-1 边权的最短路**

```cpp
// 邻接表 g[u] = vector<pair<int,int>> 存储 {邻居, 边权(0 或 1)}
// 求从 start 到所有点的最短距离

vector<long long> bfs_01(vector<vector<pair<int, int>>>& g, int n, int start) {

    const long long INF = 1e18;

    vector<long long> dist(n + 1, INF);

    deque<int> dq;

    dist[start] = 0;

    dq.push_front(start);

    while (!dq.empty()) {

        int u = dq.front();

        dq.pop_front();

        for (auto [v, w] : g[u]) {

            if (dist[u] + w < dist[v]) {

                dist[v] = dist[u] + w;

                if (w == 0) {

                    dq.push_front(v);       // 0 边：插队首

                } else {

                    dq.push_back(v);        // 1 边：插队尾

                }

            }

        }

    }

    return dist;

}
```

> ⚠️ **节点会被多次入队**：因为后续的更短路径会让节点再次被更新。所以同一节点可能在 deque 中存在多次。这不影响正确性，只是常数稍大。
  
**模板：网格图变形**

题目典型场景：网格上行走每步代价 1，但部分位置有"传送门"使代价为 0。

```cpp
// grid[i][j] 中：'.' 普通(代价1)，'*' 传送(代价0)，'#' 墙

int grid_01_bfs(vector<string>& grid, int sx, int sy, int tx, int ty) {

    int n = grid.size();

    int m = grid[0].size();

    const int INF = 1e9;

    vector<vector<int>> dist(n, vector<int>(m, INF));

    deque<pair<int, int>> dq;

    dist[sx][sy] = 0;

    dq.push_front({sx, sy});

    int dx[] = {-1, 1, 0, 0};

    int dy[] = {0, 0, -1, 1};

    while (!dq.empty()) {

        auto [x, y] = dq.front();

        dq.pop_front();

        for (int d = 0; d < 4; d++) {

            int nx = x + dx[d];

            int ny = y + dy[d];

            if (nx < 0 || nx >= n || ny < 0 || ny >= m) {

                continue;

            }

            if (grid[nx][ny] == '#') {

                continue;

            }

            int w = (grid[nx][ny] == '*') ? 0 : 1;

            if (dist[x][y] + w < dist[nx][ny]) {

                dist[nx][ny] = dist[x][y] + w;

                if (w == 0) {

                    dq.push_front({nx, ny});

                } else {

                    dq.push_back({nx, ny});

                }

            }

        }

    }

    return dist[tx][ty] == INF ? -1 : dist[tx][ty];

}
```

## 复杂度分析

- 时间复杂度：$O(n + m)$，每条边最多触发一次入队 / 出队

- 空间复杂度：$O(n)$

## 正确性证明

### deque 的单调性不变量

**核心不变量**：在 0-1 BFS 的任一时刻，deque 中元素从队首到队尾，对应的 `dist` 值**单调不降**。且队列中至多同时存在两个不同的 `dist` 值（相邻整数）。

**证明（归纳）**：

**初始化**：deque 中只有起点，平凡成立。

**保持**：假设当前不变量成立。设队首 $u$ 出队，此时 $\text{dist}[u]$ 是 deque 中最小的。考虑 $u$ 的某条出边到 $v$，权值为 $w \in \{0, 1\}$：

- **若 $w = 0$**：$\text{dist}[v]$ 被更新为 $\text{dist}[u]$（与 $u$ 同距离）。`push_front(v)` 把 $v$ 放到队首。此时 deque 队首 = $\text{dist}[u]$，与 $v$ 相同；队尾仍 ≤ $\text{dist}[u] + 1$。单调性保持，最大差 ≤ 1。✓

- **若 $w = 1$**：$\text{dist}[v]$ 更新为 $\text{dist}[u] + 1$。`push_back(v)` 放到队尾。队尾从原来的某值（必 ≤ $\text{dist}[u] + 1$）变为 $\text{dist}[u] + 1$。单调性保持。✓

由归纳，不变量始终保持。$\blacksquare$

### 队首 dist 值的单调性

**定理**：随着算法执行，每次出队的节点的 `dist` 值**单调不降**。

**证明**：由上述不变量，队列中元素 `dist` 单调不降。每次取队首，自然取的是当前最小值。下一次出队时，队列要么没变（仅 $v$ 被压到队首，但 $v$ 的 `dist` 与上一次出队相等），要么距离非严格增大。

形式化地，"出队的距离序列"$d_1, d_2, d_3, \ldots$ 是单调不减的。$\blacksquare$

### 节点首次出队时距离即最短路

**关键命题**：当节点 $u$ 第一次以**最新** `dist[u]` 值（即出队时检查 `d == dist[u]`）出队时，`dist[u]` 已经是最终最短路。

**证明（反证）**：假设 $u$ 出队时存在更短路径 $P$，长度为 $d^* < \text{dist}[u]$。

$P$ 上必有某节点 $v$ 还在 deque 中（或尚未入队），且 $\text{dist}[v] \le d^*$。

但由队首 dist 单调性——$u$ 出队意味着此刻 deque 中所有节点的 `dist` $\ge \text{dist}[u]$。所以 $\text{dist}[v] \ge \text{dist}[u] > d^*$，矛盾。$\blacksquare$

**这与 [[Dijkstra]] 的正确性证明结构完全一致**——只是用"两层 deque"代替了"优先队列"，因为边权只有两种值时，"按距离最小优先"等价于"按层处理"。

### 为什么不能扩展到任意非负边权

考虑边权 $\{0, 1, 2\}$ 的情况——若用 deque 处理，新节点 $v$ 通过权值 2 的边到达时距离为 $\text{dist}[u] + 2$。它应该排在队列里 $\text{dist}[u] + 2$ 的位置，但 deque 只能 push_front / push_back，无法插入到中间——单调性会被破坏。

所以 0-1 BFS 严格依赖"边权只有两种值"。推广到 $\{0, 1, \ldots, k\}$ 时需用 $k + 1$ 个桶，称为"桶 BFS"，但 $k > 1$ 时通常直接上 [[Dijkstra]] 更稳妥。$\blacksquare$

## 与相关算法的对比

**与 [[Dijkstra]] 的关系**：0-1 BFS 是 Dijkstra 在边权 $\in \{0, 1\}$ 下的特化。Dijkstra 的优先队列处理的是"取出当前距离最小的节点"，0-1 BFS 借助"边权只有两种值"的额外条件，把这一过程降为 $O(1)$。

**与 [[BFS]] 的关系**：边权全为 1 时，0-1 BFS 的"push_back"操作退化为普通 BFS，正确性自然继承。

## 相关例题

- [洛谷P4554 小明的游戏](https://www.luogu.com.cn/problem/P4554)