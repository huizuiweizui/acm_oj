#难度/★★★★

> 启发式搜索的代表算法——给每个状态一个"还需步数估计"，按"已用 + 估计"总和优先扩展，能在保证最优的前提下大幅剪枝。

## 前置知识

- [[BFS]]

- [[Dijkstra]]

## 核心思想

[[Dijkstra]] 总是按"已用代价 $g$ 最小"来扩展节点，对所有方向"一视同仁"。但很多问题中，我们其实**对终点有方向感**——比如在迷宫中朝着出口的方向搜显然比反向搜更有希望。

**A\*（A-star）算法**给每个节点 $u$ 计算两个值：

- $g(u)$：从起点到 $u$ 的**实际**已用代价

- $h(u)$：从 $u$ 到终点的**估计**剩余代价（启发式函数）

- $f(u) = g(u) + h(u)$：经过 $u$ 的整条路径**估计总代价**

每次从优先队列中取出 $f(u)$ 最小的节点扩展。当**估价函数 $h$ 满足"可采纳性"**（$h(u) \le$ 真实剩余代价）时，A\* 找到的第一个目标解就是最优解。

A\* 的强大之处：当 $h$ 越接近真实剩余代价时，A\* 探索的状态越少。极端情况——$h \equiv 0$ 时退化为 [[Dijkstra]]；$h$ 等于真实剩余代价时，A\* 直接走最优路径，几乎不浪费一步。

## 适用场景

- 求**单一终点**的最短路（A\* 是单源单汇算法，不像 Dijkstra 能一次性求所有点）

- 状态空间巨大但**有方向感**——如八数码、华容道、地图导航

- 能设计出合理的可采纳估价函数 $h$

- 不适用：找不到合理的 $h$（直接 [[Dijkstra]]）；终点不唯一或要求所有点的最短路（用 Dijkstra）；存在负权（用 [[SPFA]]）

## 步骤拆解

1. 定义状态、估价函数 $h(\text{state})$

2. 用优先队列 `priority_queue` 维护待扩展状态，按 $f$ 值小的优先

3. 起点入队，$g(\text{start}) = 0$，$f(\text{start}) = h(\text{start})$

4. 循环直到队空：

   a. 取出 $f$ 最小的节点 $u$

   b. 若 $u$ 是终点，返回 $g(u)$

   c. 若 $u$ 已被更优地访问过，跳过

   d. 枚举 $u$ 的每个邻居 $v$，计算新的 $g(v) = g(u) + w(u, v)$。若比已有 $g(v)$ 更小，更新并把 $(f(v), v)$ 入队

## 代码模板

**模板一：一般图上的 A\***

```cpp

// g[u] = vector<pair<int,int>> 存 {邻居, 边权}

// heuristic(u) = 从 u 到终点的估计代价（单调可采纳）

class a_star {

private:

    int n, target;

    vector<vector<pair<int, long long>>> g;

  

    int heuristic(int u) {

        // 估价函数：必须满足 h(u) <= 真实剩余代价

        // 例如，地图问题中常用曼哈顿/欧几里得距离

        return /* ... */;

    }

  

public:

    a_star(int total, vector<vector<pair<int, long long>>>& g_in, int t) {

        n = total;

        g = g_in;

        target = t;

    }

  

    long long solve(int start) {

        const long long INF = 1e18;

        vector<long long> dist(n + 1, INF);

        priority_queue<pair<long long, int>,

                       vector<pair<long long, int>>,

                       greater<>> pq;

        dist[start] = 0;

        pq.push({heuristic(start), start});

  

        while (!pq.empty()) {

            auto [f, u] = pq.top();

            pq.pop();

            if (u == target) {

                return dist[u];

            }

            // 跳过过期版本

            if (f - heuristic(u) > dist[u]) {

                continue;

            }

            for (auto [v, w] : g[u]) {

                if (dist[u] + w < dist[v]) {

                    dist[v] = dist[u] + w;

                    pq.push({dist[v] + heuristic(v), v});

                }

            }

        }

        return -1;                          // 不可达

    }

};

```

**模板二：网格图 A\***

```cpp

// 在 n×m 网格上从 (sx,sy) 到 (tx,ty) 的最短路径，'#' 为障碍

int a_star_grid(vector<string>& grid, int sx, int sy, int tx, int ty) {

    int n = grid.size();

    int m = grid[0].size();

    const int INF = 1e9;

    vector<vector<int>> dist(n, vector<int>(m, INF));

  

    auto h = [&](int x, int y) {

        return abs(x - tx) + abs(y - ty);   // 曼哈顿距离（4 方向移动时可采纳）

    };

  

    priority_queue<tuple<int, int, int>,

                   vector<tuple<int, int, int>>,

                   greater<>> pq;          // (f, x, y)

  

    dist[sx][sy] = 0;

    pq.push({h(sx, sy), sx, sy});

  

    int dx[] = {-1, 1, 0, 0};

    int dy[] = {0, 0, -1, 1};

  

    while (!pq.empty()) {

        auto [f, x, y] = pq.top();

        pq.pop();

        if (x == tx && y == ty) {

            return dist[x][y];

        }

        if (f - h(x, y) > dist[x][y]) {

            continue;

        }

        for (int d = 0; d < 4; d++) {

            int nx = x + dx[d];

            int ny = y + dy[d];

            if (nx < 0 || nx >= n || ny < 0 || ny >= m) {

                continue;

            }

            if (grid[nx][ny] == '#') {

                continue;

            }

            if (dist[x][y] + 1 < dist[nx][ny]) {

                dist[nx][ny] = dist[x][y] + 1;

                pq.push({dist[nx][ny] + h(nx, ny), nx, ny});

            }

        }

    }

    return -1;

}

```

> 💡 **`f - h(u) > dist[u]` 跳过过期版本**：A\* 中同一状态可能多次入队。出队时检查"队中记录的 g 值（即 f - h）是否仍是当前最优"，过期则跳过。这与 Dijkstra 的懒删除技巧一致。

## 估价函数的设计

**可采纳性（admissibility）**：$h(u) \le$ 从 $u$ 到终点的真实代价。这是 A\* 找到最优解的**充分条件**。

**一致性（consistency）**：$h(u) \le w(u, v) + h(v)$ 对所有边 $(u, v)$ 成立。一致性 ⇒ 可采纳性。一致性下，每个节点最多入队一次，可不需要"过期版本"判断。

**常见估价函数**：

| 问题        | 常用 $h$            |
| --------- | ----------------- |
| 网格 4 方向移动 | 曼哈顿距离             |
| 网格 8 方向移动 | 切比雪夫距离            |
| 网格自由移动    | 欧几里得距离            |
| 八数码       | 各方块到目标位置的曼哈顿距离之和  |
| 一般图       | 没有通用 $h$，可考虑离线预处理 |

> 💡 **设计 $h$ 的诀窍**：从原问题"放松约束"——例如把"必须沿格点走"放松成"可以斜着飞"，得到欧几里得距离作为下界估价。放松约束后的最优代价天然 $\le$ 原问题最优代价，自动满足可采纳性。

## 复杂度分析

- 时间复杂度：取决于估价函数质量。最坏情况退化为 Dijkstra 的 $O((n + m) \log n)$；估价完美时接近 $O(d)$（$d$ 是最优解长度）

- 空间复杂度：$O(\text{已访问状态数})$，可能很大

## 正确性证明

### A* 找到的就是最优解

**核心定理**：当估价函数 $h$ 满足**可采纳性**（$h(u) \le$ 真实剩余代价）时，A\* 算法第一次取出终点 $t$ 时，`dist[t]` 就是最短路长度。

**证明（反证）**：

设最优解的终点为 $t$，最优代价为 $C^*$。假设 A\* 第一次取出 $t$ 时，`dist[t] > C*`。

考虑最优路径 $P = (s = u_0, u_1, \ldots, u_k = t)$。在 $t$ 出队的瞬间，$P$ 上必存在一个**仍在队列中**的节点 $u$（最坏情况下是起点 $s$，但 $s$ 早已出队，所以更精确地说，存在某个**已被发现但未处理的** $P$ 上节点）。

**关键论断**：$f(u) \le C^*$。

**证明**：

- 由 $u$ 在最优路径 $P$ 上，$g(u)$（A\* 已记录的 $u$ 的最短距离）$\le P$ 上 $s$ 到 $u$ 的代价（记作 $g^*(u)$）。

- 由可采纳性，$h(u) \le$ 真实从 $u$ 到 $t$ 的最短代价。注意 $P$ 上 $u$ 到 $t$ 的代价等于 $C^* - g^*(u)$，而真实最短代价 $\le C^* - g^*(u)$（最优路径给了一个上界）。所以 $h(u) \le C^* - g^*(u)$。

- 综合：$f(u) = g(u) + h(u) \le g^*(u) + (C^* - g^*(u)) = C^*$。

而 $f(t) = \text{dist}[t] + h(t) = \text{dist}[t] + 0 > C^*$（因为终点 $h = 0$，且假设 $\text{dist}[t] > C^*$）。

由 A\* 优先扩展 $f$ 最小的节点，$u$ 应该早于 $t$ 出队——矛盾。所以 $\text{dist}[t] = C^*$。$\blacksquare$

### 可采纳性的必要性

**反例**：若 $h$ 不可采纳（即某处 $h(u) > $ 真实剩余代价），A\* 可能错过最优解。

考虑节点 $u$ 在最优路径上，但 $h(u)$ 高估了从 $u$ 到 $t$ 的代价——即 $h(u) > C^* - g^*(u)$。则 $f(u) > C^*$，可能比某条次优路径上的某节点 $f$ 值更大，导致 $u$ 在 $t$ 出队前一直没被扩展。当 $t$ 通过次优路径出队时，A\* 错误地返回了次优代价。

所以可采纳性是 A\* 正确性的**必要条件**。$\blacksquare$

### 一致性的额外好处

**命题**：若 $h$ 满足一致性（$h(u) \le w(u, v) + h(v)$），则每个节点最多被处理一次，`dist[u]` 一旦设置就不再被更新。

**证明**：一致性等价于"$f$ 值沿任何路径单调不降"——即若 $u \to v$ 是一条边：

  

$$f(v) = g(v) + h(v) = g(u) + w(u, v) + h(v) \ge g(u) + h(u) = f(u)$$

由 A\* 按 $f$ 最小优先扩展，每个节点出队时 $f$ 值已是它的最小值，后续不会有更小的 $f$ 路径——所以无需重新处理。这与 [[Dijkstra]] 的"出队即定值"性质一致。

可采纳但不一致的 $h$ 仍然能保证最优解，但同一节点可能多次入队（需要"过期版本"判断），常数稍大。$\blacksquare$

### 与 [[Dijkstra]] 的关系

**关系**：A\* 是 Dijkstra 的进化版——堆里的优先级是 `dist[u] + h(u)`（h 为估价函数）。当 $h \equiv 0$ 时退化为 Dijkstra（恒满足可采纳和一致性）。

**$h$ 越准 A\* 越高效**：

- $h \equiv 0$：A\* 退化为 [[Dijkstra]]，对所有方向均匀扩展

- $h$ 等于真实剩余代价：A\* 沿最优路径一路走到终点，一步弯路都不绕

- $h$ 不可采纳（高估）：A\* 可能找到次优解（错过更优解）

- $h$ 可采纳但松散：A\* 仍正确，但效率类似 Dijkstra

**A\* vs IDA\***：A\*（[[迭代加深]]+估价）空间 $O(d)$，A\* 空间可能很大；A\* 通常时间更优。两者各有适用场景。

## 相关例题

*[待补充]*
