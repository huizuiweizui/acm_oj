#难度/★★★

> Bellman-Ford 的队列优化版：只把"刚被松弛过的节点"重新入队等待检查，能处理含负权边的最短路并判定负环。

## 前置知识

- [[队列]]

- [[BFS]]

## 核心思想

[[Dijkstra]] 不能处理负权边——证明的关键步骤"路径剩余部分边权非负"在负权下失效。处理负权边的经典算法是 **Bellman-Ford**：

> 重复 $n - 1$ 轮，每轮枚举所有 $m$ 条边并尝试松弛。

复杂度 $O(nm)$。它能正确求出含负权（无负环）图的最短路，但效率较低。

**关键观察**：在 Bellman-Ford 的某一轮中，若某节点 $u$ 的 `dist[u]` 没有变化，那 $u$ 出去的所有边在本轮也不可能产生新的松弛（因为松弛条件 `dist[u] + w < dist[v]` 的左侧没变）。

**SPFA**（Shortest Path Faster Algorithm）正是基于这个观察的"懒优化"：

- 用一个队列维护**待检查**的节点

- 每次出队 $u$，遍历它的所有出边松弛邻居

- 若某邻居 $v$ 被成功松弛，且 $v$ 不在队列中，就把 $v$ 入队

这样跳过了所有"`dist` 未变"的节点，避免无谓的边检查。

**实测平均复杂度**约为 $O(km)$，$k$ 是与图结构相关的小常数（经验值 $2 \sim 3$）；**最坏情况**仍是 $O(nm)$，且容易被特殊数据卡到上界。

## 适用场景

- 含负权边但**无负环**的最短路

- 判断图中是否存在负环（从某点能无限松弛的环）

- 差分约束系统（把不等式约束转化为图，用 SPFA 求可行解）

- 不适用：边权非负（用 [[Dijkstra]]，更稳定）；图能被构造卡到 $O(nm)$（如网格图、专门的反 SPFA 数据）

## 步骤拆解

1. 初始化 `dist[s] = 0`，其他为 $+\infty$；`in_queue[]` 全为 `false`

2. 把 $s$ 入队，`in_queue[s] = true`

3. 循环直到队列空：

   a. 出队 $u$，置 `in_queue[u] = false`

   b. 枚举每条出边 $(u, v, w)$

   c. 若 `dist[u] + w < dist[v]`：更新 `dist[v]`；若 $v$ 不在队列中，入队并标记

4. 判负环：若某节点入队次数 $\ge n$，存在负环

## 代码模板

**模板一：基础 SPFA 求最短路**：

```cpp

class spfa {

private:

    int n;

    vector<vector<pair<int, long long>>> g;

public:

    spfa(int total, vector<vector<pair<int, long long>>>& g_in) {

        n = total;

        g = g_in;

    }

    // 返回 dist 数组；若存在从 start 可达的负环，返回空向量
    vector<long long> shortest_path(int start) {

        const long long INF = 1e18;

        vector<long long> dist(n + 1, INF);

        vector<bool> in_queue(n + 1, false);

        vector<int> cnt(n + 1, 0);              // 入队次数

        queue<int> q;

        dist[start] = 0;

        q.push(start);

        in_queue[start] = true;

        while (!q.empty()) {

            int u = q.front();

            q.pop();

            in_queue[u] = false;

            for (auto [v, w] : g[u]) {

                if (dist[u] + w < dist[v]) {

                    dist[v] = dist[u] + w;

                    if (!in_queue[v]) {

                        q.push(v);

                        in_queue[v] = true;

                        cnt[v] += 1;

                        if (cnt[v] >= n) {

                            return {};           // 检测到负环

                        }

                    }

                }

            }

        }

        return dist;

    }

};
```

> 💡 **`in_queue[]` 的作用**：避免同一节点同时存在于队列中多次。如果不标记，节点 $v$ 可能被反复入队，队列膨胀严重——尤其当 $v$ 是某些"枢纽"节点时。

> 💡 **判负环的原理**：无负环时，任一节点的最短路至多包含 $n - 1$ 条边——其对应的 `dist` 至多被松弛 $n - 1$ 次，所以入队次数 $\le n - 1$。若入队次数 $\ge n$，必然存在某条"反复变短"的环，即负环。

**模板二：SLF（Smallest Label First）优化**：

把队列换成双端队列，新节点入队时与队首比较——若 `dist[新] < dist[队首]`，从队首插入；否则从队尾插入。这是 SPFA 的常用常数优化：

```cpp

deque<int> q;

// 入队部分修改为：
if (!in_queue[v]) {

    if (!q.empty() && dist[v] < dist[q.front()]) {

        q.push_front(v);

    } else {

        q.push_back(v);

    }

    in_queue[v] = true;

}
```

> ⚠️ **SLF 在含负权时可能出错**：因为 `dist[v]` 后续还可能被进一步松弛，"队首总是 dist 最小"的不变量难以维持。一般稠密非负图的优化场景才用 SLF——但那种场景应该直接上 Dijkstra。

## 复杂度分析

- 时间复杂度：

  - 平均：$O(km)$，$k$ 为小常数

  - 最坏：$O(nm)$

- 空间复杂度：$O(n + m)$

## 正确性证明

### Bellman-Ford 的正确性（基础）

**引理**：在无负环的图中，从 $s$ 到任一可达节点 $v$ 的最短路至多含 $n - 1$ 条边。

**证明**：若路径含 $\ge n$ 条边，则路径上至少有 $n + 1$ 个节点（含重复）——由鸽巢原理必有节点重复出现，即路径含环。环长 $\ge 0$（无负环），删去该环路径长度不增——所以总能找到一条边数 $\le n - 1$ 的最短路。$\blacksquare$

**Bellman-Ford 主定理**：经过 $n - 1$ 轮"对所有边做一次松弛"后，所有节点的 `dist` 都等于真实最短路。

**证明（归纳）**：设 $v$ 的真实最短路边数为 $k$（$k \le n - 1$），路径为 $s = v_0 \to v_1 \to \cdots \to v_k = v$。

对 $i$ 归纳证明：经过第 $i$ 轮松弛后，$\mathtt{dist}[v_i]$ 已等于 $s \to v_i$ 的真实最短路。

- $i = 0$：$\mathtt{dist}[v_0] = \mathtt{dist}[s] = 0$，初始化即正确。

- $i \to i + 1$：归纳假设 $\mathtt{dist}[v_i]$ 已正确。第 $i + 1$ 轮中，边 $(v_i, v_{i+1})$ 必被检查，触发松弛 $\mathtt{dist}[v_{i+1}] \leftarrow \mathtt{dist}[v_i] + w(v_i, v_{i+1})$，正是真实最短路。

由 $k \le n - 1$，$n - 1$ 轮足以让所有最短路被找到。$\blacksquare$

### SPFA 的正确性

**核心命题**：SPFA 与 Bellman-Ford 求出的最短路完全一致。

**证明**：考察任一被松弛的边 $(u, v, w)$——即 $\mathtt{dist}[u] + w < \mathtt{dist}[v]$。

在 Bellman-Ford 中，每轮都会检查这条边。在 SPFA 中，松弛触发于"$u$ 出队的时刻"——而 $u$ 出队仅当 $u$ 此前被某次松弛过（除起点外）并入队。

关键观察：**若某条边在 Bellman-Ford 的某轮中产生了松弛，则该边的左端点 $u$ 在前一轮中必有 $\mathtt{dist}[u]$ 的更新**——而 SPFA 把"$\mathtt{dist}[u]$ 更新"作为入队信号，$u$ 入队后必将检查 $(u, v, w)$ 这条边。所以 Bellman-Ford 中所有"有效松弛"在 SPFA 中也会被执行。

具体地，对路径 $s = v_0 \to v_1 \to \cdots \to v_k = v$ 用归纳法：$v_i$ 被首次正确松弛后必入队，出队时检查 $(v_i, v_{i+1})$ 触发对 $v_{i+1}$ 的松弛。所以在 SPFA 终止时，所有节点的 `dist` 等于真实最短路。$\blacksquare$

### 负环判定的正确性

**命题**：算法终止时，若某节点入队次数 $\ge n$，则图中存在从 $s$ 可达的负环。

**证明（反向）**：

若图中无从 $s$ 可达的负环，由"无负环图最短路边数 $\le n - 1$"的引理，每个节点的 `dist` 至多被松弛 $n - 1$ 次（每次松弛对应路径边数 +1，超过 $n - 1$ 必有更短的路径）。所以入队次数 $\le n - 1 < n$。

逆否：若入队次数 $\ge n$，必存在负环。$\blacksquare$

**命题**：若存在从 $s$ 可达的负环，算法必能检测到。

**证明**：负环上的节点的 `dist` 可以通过绕环不断变小，松弛次数无界——必然某节点入队次数超过 $n$，被检测到。$\blacksquare$

### 为什么会被卡到 $O(nm)$

构造一个"链 + 反向边"的图：节点 $1, 2, \ldots, n$ 串成链，并加入若干反向短路边。SPFA 会反复松弛同一节点——某节点甚至可能被入队 $\Theta(n)$ 次，每次出队检查 $\Theta(m / n)$ 条边，总计 $O(nm)$。

更糟的是，常见的网格 + 负权混合图都能制造这种最坏情况。

**这就是"SPFA 已死"的原因**：复杂度上界存在但形同虚设，被精心构造的数据可以稳稳卡死。

## 相关例题

- [洛谷P3385 【模板】负环](https://www.luogu.com.cn/problem/P3385)

- [洛谷P5960 【模板】差分约束](https://www.luogu.com.cn/problem/P5960)