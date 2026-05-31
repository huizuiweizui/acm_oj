#难度/★★

> 一种"按层逐步扩散"的搜索策略，用队列实现，是无权图最短路与"最少步数"问题的标准解法。

## 前置知识

- [[队列]]

## 核心思想

BFS（Breadth-First Search，广度优先搜索）的核心是**先访问完当前层的所有节点，再访问下一层**。配合"已访问标记"，每个节点第一次被访问时**走过的边数（即层数）就是从起点到它的最短步数**——这是 BFS 最重要的性质。

实现上，BFS 用一个 [[队列]] 维护待扩展的节点：

- 起点入队

- 每次取出队首，把它所有**未访问**的邻居入队，并标记为已访问

- 队列空时遍历完成

由于队列的 FIFO 性质，节点是**按层入队、按层出队**的——这是 BFS 与 [[DFS]]（用栈，LIFO）的本质区别。

## 适用场景

- **无权图最短路**：求从起点到每个点的**最少边数**（最经典应用）

- **最少步数问题**：八数码、迷宫最少步数、状态变换的最少操作数

- 求图的连通性、连通分量（与 [[DFS]] 等价，BFS 用循环不易爆栈）

- 求层序信息：树的层序遍历、二分图染色

- 配合状态压缩处理状态空间问题（见 [[状压BFS]]）

- 边权只有 0/1 时的最短路（见 [[0-1 BFS]]）

- 不适用：边权任意非负（应用 [[Dijkstra]]）；要求枚举所有方案（应用 [[DFS]]）

## 步骤拆解

**BFS 标准框架**：

1. 初始化 `dist[]` 为 $-1$（表示未访问），`dist[start] = 0`

2. 起点入队

3. 循环直到队列为空：

   a. 取出队首 $u$

   b. 枚举 $u$ 的每个邻居 $v$

   c. 若 $v$ 未访问（`dist[v] == -1`）：设置 `dist[v] = dist[u] + 1`，把 $v$ 入队

4. 若需要还原路径，可额外维护 `parent[]` 数组

## 代码模板

**模板一：网格图最短路（迷宫问题）**

```cpp
// grid 中 0 表示空地，1 表示障碍。求从 (sx, sy) 到 (tx, ty) 的最少步数
int bfs_grid(vector<vector<int>>& grid, int sx, int sy, int tx, int ty) {

    int n = grid.size() - 1;

    int m = grid[0].size() - 1;

    vector<vector<int>> dist(n + 1, vector<int>(m + 1, -1));

    queue<pair<int, int>> q;

    dist[sx][sy] = 0;

    q.push({sx, sy});

    int dx[] = {-1, 1, 0, 0};           // 上、下、左、右

    int dy[] = {0, 0, -1, 1};

    while (!q.empty()) {

        auto [x, y] = q.front();

        q.pop();

        if (x == tx && y == ty) {

            return dist[x][y];

        }

        for (int d = 0; d < 4; d++) {

            int nx = x + dx[d];

            int ny = y + dy[d];

            if (nx < 1 || nx > n || ny < 1 || ny > m) {

                continue;

            }

            if (grid[nx][ny] == 1 || dist[nx][ny] != -1) {

                continue;

            }

            dist[nx][ny] = dist[x][y] + 1;

            q.push({nx, ny});

        }

    }

    return -1;                          // 不可达

}
```

> 💡 **`dx[] / dy[]` 数组的妙用**：把"四个方向"或"八个方向"统一成一个循环，避免写四份对称代码。这是网格 BFS 的标准技巧。

**模板二：图上 BFS（求所有点到起点的最短距离）**

```cpp
class bfs_graph {

private:

    int n;

    vector<vector<int>> g;

public:

    bfs_graph(int total, vector<vector<int>>& g_in) {

        n = total;

        g = g_in;

    }

    vector<int> shortest_distance(int start) {

        vector<int> dist(n + 1, -1);

        queue<int> q;

        dist[start] = 0;

        q.push(start);

        while (!q.empty()) {

            int u = q.front();

            q.pop();

            for (int v : g[u]) {

                if (dist[v] == -1) {

                    dist[v] = dist[u] + 1;

                    q.push(v);

                }

            }

        }

        return dist;

    }

};
```

**模板三：BFS 还原最短路径**

```cpp
vector<int> bfs_path(vector<vector<int>>& g, int n, int start, int target) {

    vector<int> dist(n + 1, -1);

    vector<int> parent(n + 1, 0);

    queue<int> q;

    dist[start] = 0;

    q.push(start);

    while (!q.empty()) {

        int u = q.front();

        q.pop();

        if (u == target) {

            break;

        }

        for (int v : g[u]) {

            if (dist[v] == -1) {

                dist[v] = dist[u] + 1;

                parent[v] = u;

                q.push(v);

            }

        }

    }

    if (dist[target] == -1) {

        return {};                      // 不可达

    }

    // 沿 parent 回溯路径
    vector<int> path;

    for (int u = target; u != 0; u = parent[u]) {

        path.push_back(u);

    }

    reverse(path.begin(), path.end());

    return path;

}
```

## 复杂度分析

- 时间复杂度：$O(n + m)$（$n$ 节点数，$m$ 边数），每个节点入队/出队各一次

- 空间复杂度：$O(n)$（队列 + dist 数组）

## 正确性证明

### BFS 求出的就是最短路

**关键定理**：当节点 $u$ 第一次被访问（即 `dist[u]` 第一次被设置）时，`dist[u]` 就是从起点 $s$ 到 $u$ 的最短距离（边数）。

**循环不变量**：在 BFS 的任一时刻，队列中元素的 `dist` 值满足"从队首到队尾单调不降，且最大值与最小值相差至多 1"。即队列中至多同时存在两层节点。

**证明（归纳法对距离 $d$）**：

**基础情形**：$\text{dist}[s] = 0$，显然是 $s$ 到自己的最短距离。

**归纳步骤**：假设所有真实距离 $\le d - 1$ 的节点都已被正确赋值。考虑某节点 $v$ 的真实最短距离恰为 $d$，要证它会被赋值为 $d$。

由真实距离为 $d$，存在路径 $s = u_0 \to u_1 \to \cdots \to u_d = v$，其中 $u_{d-1}$ 真实距离为 $d - 1$。由归纳假设，$\text{dist}[u_{d-1}]$ 已被赋值为 $d - 1$，且 $u_{d-1}$ 已入队。

当 $u_{d-1}$ 出队扩展邻居时，会枚举到 $v$。此时 $v$ 的状态有两种可能：

- $v$ 尚未被访问（`dist[v] == -1`）：会被赋值 $\text{dist}[v] = \text{dist}[u_{d-1}] + 1 = d$，正确。

- $v$ 已被访问：说明在 $u_{d-1}$ 出队前 $v$ 就被某节点 $u'$ 赋值过。由队列的 FIFO 性质——先入队的先出队——$u'$ 的入队时间不晚于 $u_{d-1}$，而 $\text{dist}[u'] \le \text{dist}[u_{d-1}] = d - 1$。因此 $\text{dist}[v] = \text{dist}[u'] + 1 \le d$。

但 $d$ 是 $v$ 的真实最短距离，$\text{dist}[v]$ 不可能 $< d$（否则发现了更短路径与 $d$ 是最短矛盾）。所以 $\text{dist}[v] = d$。

由归纳，所有节点的 `dist` 都等于真实最短距离。$\blacksquare$

### 入队即标记的必要性

**命题**：必须在节点**入队时**而非**出队时**标记 visited，否则可能重复入队。

**反证**：若改为出队时才标记，考虑节点 $v$ 距起点 2 步，有两个邻居 $u_1, u_2$ 都距起点 1 步。$u_1$ 出队时把 $v$ 入队（$v$ 标记还没设）；$u_2$ 出队时——此时 $v$ 还没出队所以未被标记——又把 $v$ 入队。$v$ 入队两次。

不仅浪费空间，更严重的是 `dist[v]` 会被设置两次（第二次覆盖第一次），但由于第二次的 `dist[v] = dist[u_2] + 1` 与第一次相等（$u_1, u_2$ 同层），结果仍正确——只是效率退化为指数。

更糟的情况：若图中存在重边或多入口，重复入队可能让队列指数级膨胀，整个 BFS 直接 TLE。$\blacksquare$

### 为什么用队列而不是栈

**反证**：若把 BFS 中的队列换成栈，每次取出"最近加入"的节点扩展——这就退化成 [[DFS]]。栈不保留"按层"性质，深度优先地去探索某一支路径，第一次到达目标时可能不是最短路径。

队列的 FIFO 保证"早入队的先扩展"——配合"每层节点入队前其上一层已全部入队"的归纳，距离按层单调推进。这是 BFS 与 DFS 的根本分野。$\blacksquare$

## 与 [[DFS]] 的对比

| 维度         | DFS                   | BFS                 |
| ---------- | --------------------- | ------------------- |
| 数据结构       | 栈（递归隐式 / 显式手写）        | 队列                  |
| 探索顺序       | 深入到底再回溯               | 按层扩散                |
| 空间         | $O(\text{深度})$        | $O(\text{宽度})$      |
| 求最短步数      | ❌                     | ✅                   |
| 枚举所有方案     | ✅                     | ❌                   |
| 求连通性       | ✅                     | ✅                   |
| 路径还原       | 较麻烦                   | 简单（parent 数组）       |

## 相关例题

- [洛谷P1443 马的遍历](https://www.luogu.com.cn/problem/P1443)