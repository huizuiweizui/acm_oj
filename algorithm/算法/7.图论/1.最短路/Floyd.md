#难度/★★★ 

> 三重循环 dp，$O(n^3)$ 求**所有点对**最短路，对负权友好，代码极短。

## 核心思想

Floyd 算法（也称 Floyd-Warshall）求**全源最短路**——一次性算出图中任意两点 $i, j$ 之间的最短距离。

它的核心是一个 dp：

> $f[k][i][j]$ = 只允许使用编号在 $\{1, 2, \ldots, k\}$ 中的节点作为**中转点**时，$i \to j$ 的最短路。

转移方程：

$$f[k][i][j] = \min\left(\, f[k-1][i][j],\; f[k-1][i][k] + f[k-1][k][j] \,\right)$$

含义是——从 $i$ 到 $j$ 的最短路要么不经过 $k$（保持 $f[k-1][i][j]$），要么经过 $k$（拆成 $i \to k$ 和 $k \to j$ 两段，每段又只能用编号 $\le k - 1$ 的节点中转）。

边界条件：$f[0][i][j] = w(i, j)$（直接边的权值，无边为 $+\infty$，自环为 0）。

最终答案：$f[n][i][j]$ 即任意两点最短路。

**滚动优化**：转移中 $f[k][\cdot][\cdot]$ 只依赖 $f[k-1][\cdot][\cdot]$，所以可以**只用一个二维数组** `dist[i][j]` 反复更新——这就是经典的"三重循环"写法。但要小心循环顺序。

## 适用场景

- **全源最短路**：$n$ 较小时（$n \le 500$）的标配

- 含负权边但无负环

- **传递闭包**：把"边权"换成"是否可达"，把 `min, +` 换成 `or, and`，可求出"$i$ 是否能到达 $j$"

- **图上 dp 问题**：有些题目本质就是"枚举中转点"的 dp，用 Floyd 框架天然契合

- 不适用：$n > 500$（$n^3$ 不可行）；只关心单源最短路（$n$ 次 Dijkstra 可能更快）；存在负环（要专门检测）

## 步骤拆解

1. 初始化 `dist[i][j]`：自环为 0，直接边为 $w(i, j)$，无边为 $+\infty$

2. 三重循环：$k$ 从 1 到 $n$（**最外层**），$i, j$ 从 1 到 $n$

3. 每次尝试松弛：若 `dist[i][k] + dist[k][j] < dist[i][j]`，则更新

## 代码模板

**模板一：经典 Floyd**：

```cpp

class floyd {

private:

    int n;

    vector<vector<long long>> dist;

public:

    floyd(int total, vector<tuple<int, int, long long>>& edges) {

        n = total;

        const long long INF = 1e18;

        dist.assign(n + 1, vector<long long>(n + 1, INF));

        for (int i = 1; i <= n; i++) {

            dist[i][i] = 0;

        }

        for (auto& [u, v, w] : edges) {

            dist[u][v] = min(dist[u][v], w);    // 取重边的最小值

        }

        // 三重循环：k 必须在最外层
        for (int k = 1; k <= n; k++) {

            for (int i = 1; i <= n; i++) {

                for (int j = 1; j <= n; j++) {

                    if (dist[i][k] < INF && dist[k][j] < INF) {

                        if (dist[i][k] + dist[k][j] < dist[i][j]) {

                            dist[i][j] = dist[i][k] + dist[k][j];

                        }

                    }

                }

            }

        }

    }

    long long query(int i, int j) {

        return dist[i][j];

    }

};
```

> ⚠️ **$k$ 必须在最外层**：循环顺序写错的话，转移方程的"前一阶段"假设被破坏，结果错误。详见正确性证明部分。

> 💡 **判 `INF` 的必要性**：若直接 `dist[i][k] + dist[k][j]`，两个 `INF` 相加会溢出。用 `long long INF = 1e18` 加和不会爆，但若用 `int` 必须先判断。

**模板二：传递闭包（判可达性）**：

```cpp

// reach[i][j] = i 是否能到达 j
vector<vector<bool>> reach(n + 1, vector<bool>(n + 1, false));

for (int i = 1; i <= n; i++) {

    reach[i][i] = true;

}

// 读入边后...
for (int k = 1; k <= n; k++) {

    for (int i = 1; i <= n; i++) {

        for (int j = 1; j <= n; j++) {

            if (reach[i][k] && reach[k][j]) {

                reach[i][j] = true;

            }

        }

    }

}
```

**模板三：还原最短路径**：

维护一个 `next[i][j]` 表示从 $i$ 到 $j$ 的最短路上，离开 $i$ 走的下一个节点：

```cpp

vector<vector<int>> nxt(n + 1, vector<int>(n + 1, 0));

// 初始化：直接边 nxt[i][j] = j
for (auto& [u, v, w] : edges) {

    nxt[u][v] = v;

}

// 转移时同步更新
if (dist[i][k] + dist[k][j] < dist[i][j]) {

    dist[i][j] = dist[i][k] + dist[k][j];

    nxt[i][j] = nxt[i][k];                       // 关键：走向 k 的第一步

}

// 还原 i 到 j 的路径
vector<int> path = {i};

int cur = i;

while (cur != j) {

    cur = nxt[cur][j];

    path.push_back(cur);

}
```

## 复杂度分析

- 时间复杂度：$O(n^3)$

- 空间复杂度：$O(n^2)$

## 正确性证明

### dp 转移方程的正确性

**命题**：$f[k][i][j] = \min\left(f[k-1][i][j],\; f[k-1][i][k] + f[k-1][k][j]\right)$ 是 $f[k][i][j]$ 的正确递推。

**证明**：考虑 $i \to j$ 中转点编号都在 $\{1, \ldots, k\}$ 的最优路径 $P^*$。分两种情况：

- $P^*$ 不经过 $k$：则它的中转点都在 $\{1, \ldots, k - 1\}$ 中，$|P^*| = f[k - 1][i][j]$。

- $P^*$ 经过 $k$：在 $P^*$ 上 $k$ 必出现一次（**不可能多次**——否则 $P^*$ 含环，无负环时去环不增长度，矛盾于 $P^*$ 最优）。把 $P^*$ 沿 $k$ 切成两段 $i \to k$ 和 $k \to j$，每段中转点都在 $\{1, \ldots, k - 1\}$ 中，所以 $|P^*| = f[k - 1][i][k] + f[k - 1][k][j]$。

取两者最小即得方程。$\blacksquare$

### 滚动数组的合法性（$k$ 必须最外层）

**关键问题**：转移方程是 $f[k] \leftarrow f[k - 1]$，但代码中我们用同一个 `dist[][]` 数组反复更新——读取 `dist[i][k]` 时它可能是 $f[k - 1][i][k]$（旧值）也可能是 $f[k][i][k]$（已更新的新值）。这会出错吗？

**关键引理**：在第 $k$ 轮中，$f[k][i][k] = f[k - 1][i][k]$ 且 $f[k][k][j] = f[k - 1][k][j]$，即"经过 $k$ 自身"的转移退化到"不经过 $k$"。

**证明**：以 $f[k][i][k]$ 为例，套转移方程：

$$f[k][i][k] = \min\left(f[k-1][i][k],\; f[k-1][i][k] + f[k-1][k][k]\right)$$

而 $f[k-1][k][k] = 0$（自身到自身距离 0，无负环时是最优的——若有负权自环就退化为负值，但题目通常无）。所以 $f[k][i][k] = f[k-1][i][k]$。同理 $f[k][k][j] = f[k-1][k][j]$。$\blacksquare$

**滚动数组的正确性**：在第 $k$ 轮处理 `dist[i][j]` 时，无论 `dist[i][k]` 此刻是 $f[k-1][i][k]$ 还是 $f[k][i][k]$，由上引理两者相等——**读到哪个值都不影响结果**。所以单数组覆盖式更新是合法的。

**但必须 $k$ 在最外层**：若 $k$ 在内层，比如循环顺序为 $i, j, k$——固定 $i, j$ 后 $k$ 从 1 到 $n$ 跑——此时不是按"中转点编号"的轮次推进，dp 阶段被打乱，正确性不再成立。$\blacksquare$

### 边界与初值

初始化 $f[0][i][j] = w(i, j)$（无边为 $+\infty$，自环为 0）正是"不允许任何中转点"时的最短路——直接边权。所以 $k = 0$ 时方程已正确。归纳保证 $f[n][i][j]$ 即为最终最短路。$\blacksquare$

### 负环检测

无负环时，所有 $f[k][i][i] \ge 0$（每个节点到自己的最短路至少为 0）。

**判定**：若算法终止时存在 `dist[i][i] < 0`，则图中存在负环。

**证明**：`dist[i][i] < 0` 意味着存在从 $i$ 出发回到 $i$ 的负权路径——这就是负环。$\blacksquare$

## 与相关算法的对比

| 维度         | Floyd       | Dijkstra × n               | SPFA × n               |
| ---------- | ----------- | -------------------------- | ---------------------- |
| 用途         | 全源          | 全源                         | 全源                     |
| 复杂度        | $O(n^3)$    | $O(n \cdot (n+m) \log n)$  | 平均 $O(nkm)$            |
| 边权         | 任意（无负环）     | 非负                         | 任意（无负环）                |
| 代码量        | 极短（10 行）    | 较短                         | 较短                     |
| 适合规模       | $n \le 500$ | 稀疏图 $n \le 5000$           | 不推荐                    |


**经验**：$n \le 400$ 直接 Floyd，写起来最快；$n$ 较大但稀疏（$m$ 远小于 $n^2$）跑 $n$ 次 Dijkstra 更快。

## 相关例题

- [洛谷B3647 【模板】Floyd 算法](https://www.luogu.com.cn/problem/B3647)

- [洛谷P1119 灾后重建](https://www.luogu.com.cn/problem/P1119)