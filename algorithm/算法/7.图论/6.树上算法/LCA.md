#难度/★★★

> 找出树中两个节点的最低公共祖先——倍增法预处理 $O(n \log n)$，每次查询 $O(\log n)$。

## 前置知识

- [[倍增]]

- [[DFS]]

## 核心思想

**最低公共祖先（Lowest Common Ancestor, LCA）**：树中两个节点 $u, v$ 的祖先有很多（共同祖先），其中**深度最大**的那个就是 LCA。直观地说，LCA 是 $u$ 与 $v$ 在树上"最先汇合"的点。

LCA 在树上路径问题中无处不在——从 $u$ 到 $v$ 的路径经过 $\mathrm{lca}(u, v)$ 这个"折点"，路径长度可表示为：

$$\mathtt{dist}(u, v) = \mathtt{depth}[u] + \mathtt{depth}[v] - 2 \cdot \mathtt{depth}[\mathrm{lca}(u, v)]$$

求 LCA 有多种算法：

- **倍增法**：预处理 $\mathtt{fa}[u][k] = u$ 的 $2^k$ 级祖先，查询时一步步"跳跃"（最常用）

- **欧拉序 + RMQ**：用 [[ST表]] 在欧拉序上做区间最值查询，查询 $O(1)$

- **Tarjan 离线算法**：把所有查询离线后一次 DFS 处理，配合并查集

- **树链剖分**：用 [[树链剖分]] 也能在 $O(\log n)$ 求 LCA

**倍增法核心**——树上的"二进制跳跃"：

预处理 $\mathtt{fa}[u][k]$ 表示 $u$ 的 $2^k$ 级祖先（$\mathtt{fa}[u][0]$ 是父亲）。递推：

$$\mathtt{fa}[u][k] = \mathtt{fa}[\mathtt{fa}[u][k-1]][k-1]$$

即"先跳 $2^{k-1}$ 步，再跳 $2^{k-1}$ 步"。任何步数 $d$ 都能由二进制位拆成 $2^k$ 的和——所以从 $u$ 跳到任意祖先只需 $O(\log n)$ 步。

查询 $\mathrm{lca}(u, v)$ 分两步：

1. **统一深度**：把更深的那个上跳到与对方同深度

2. **同步跳跃**：$u, v$ 同时倍增上跳，每次跳到"再跳一步就相遇"的位置——最终 $\mathtt{fa}[u][0] = \mathtt{fa}[v][0]$ 就是 LCA

> 💡 **同步跳跃为什么是从大到小试**：贪心地从大步开始尝试——若能跳就跳（即跳后两点仍不同），否则不跳。结束时 $u, v$ 是 LCA 的两个不同子节点，再上一步就是 LCA。

## 适用场景

- **树上路径长度**：$\mathtt{dist}(u, v) = \mathtt{depth}[u] + \mathtt{depth}[v] - 2 \cdot \mathtt{depth}[\mathrm{lca}]$

- **树上路径求和 / 最值**：用 [[树上前缀和与差分]] 配合 LCA 处理路径

- 判断 $u$ 是否是 $v$ 的祖先：$\mathrm{lca}(u, v) = u$

- 求两点间路径上的某种属性（用 [[树链剖分]] 或前缀和 + LCA）

- **离线处理**：很多树上问题可以通过 LCA + dfs 序转化

- 不适用：单次只查一两个 LCA 但不预处理（直接暴力上跳更快）；动态加点 / 删点的森林（用 LCT）

## 步骤拆解

**预处理**：

1. 选定根节点（一般取 1）

2. DFS 计算 $\mathtt{depth}[u]$

3. DFS 中递推 $\mathtt{fa}[u][0] = $ 父节点；$\mathtt{fa}[u][k] = \mathtt{fa}[\mathtt{fa}[u][k-1]][k-1]$（$k \ge 1$）

4. $k$ 的上界 $\log_n = \lceil \log_2 n \rceil$

**查询 $\mathrm{lca}(u, v)$**：

1. 若 $\mathtt{depth}[u] < \mathtt{depth}[v]$，交换 $u, v$（保证 $u$ 是更深的）

2. 把 $u$ 上跳到与 $v$ 同深度——把深度差按二进制拆，对每个 1 位跳一次

3. 若 $u = v$，已找到 LCA

4. 否则从大到小尝试 $k = \log_n, \ldots, 0$：若 $\mathtt{fa}[u][k] \ne \mathtt{fa}[v][k]$，则 $u, v$ 同时上跳 $2^k$ 步

5. 最终 $\mathtt{fa}[u][0]$ 就是 LCA

## 代码模板

**模板：倍增法 LCA**

```cpp

class lca_binary_lifting {

private:

    int n, log_n;

    vector<vector<int>> g;

    vector<vector<int>> fa;                     // fa[u][k] = u 的 2^k 级祖先

    vector<int> depth;

    void dfs(int u, int parent, int d) {

        depth[u] = d;

        fa[u][0] = parent;

        for (int k = 1; k <= log_n; k++) {

            fa[u][k] = fa[fa[u][k - 1]][k - 1];

        }

        for (int v : g[u]) {

            if (v != parent) {

                dfs(v, u, d + 1);

            }

        }

    }

public:

    lca_binary_lifting(int total, vector<vector<int>>& g_in, int root) {

        n = total;

        g = g_in;

        log_n = 0;

        while ((1 << log_n) <= n) {

            log_n += 1;

        }

        fa.assign(n + 1, vector<int>(log_n + 1, 0));

        depth.assign(n + 1, 0);

        dfs(root, 0, 0);                        // 0 表示根的"父节点"哨兵

    }

    int query(int u, int v) {

        // 1. 统一深度

        if (depth[u] < depth[v]) {

            swap(u, v);

        }

        int diff = depth[u] - depth[v];

        for (int k = 0; k <= log_n; k++) {

            if ((diff >> k) & 1) {

                u = fa[u][k];

            }

        }

        if (u == v) {

            return u;

        }

        // 2. 同步上跳

        for (int k = log_n; k >= 0; k--) {

            if (fa[u][k] != fa[v][k]) {

                u = fa[u][k];

                v = fa[v][k];

            }

        }

        return fa[u][0];

    }

    int dist(int u, int v) {

        return depth[u] + depth[v] - 2 * depth[query(u, v)];

    }

};

```

> 💡 **哨兵节点**：把"根的父节点"设为 0，且 $\mathtt{fa}[0][k] = 0$ 对所有 $k$。这样跳到根再跳上去仍停在 0，不会越界。

> ⚠️ **预处理时的递推顺序**：必须先填好 $\mathtt{fa}[u][0]$，再用同一节点的 $k - 1$ 阶填 $k$ 阶——但要求 $\mathtt{fa}[\mathtt{fa}[u][k-1]][k-1]$ 已知。在 DFS 中按"父节点先于子节点"的顺序自然满足。

## 复杂度分析

- 预处理：$O(n \log n)$

- 单次查询：$O(\log n)$

- 空间：$O(n \log n)$

## 正确性证明

### 倍增数组的正确性

**命题**：递推 $\mathtt{fa}[u][k] = \mathtt{fa}[\mathtt{fa}[u][k-1]][k-1]$ 正确给出 $u$ 的 $2^k$ 级祖先。

**证明（归纳）**：

**基础** $k = 0$：$\mathtt{fa}[u][0]$ 即父节点，是 $u$ 的 $2^0 = 1$ 级祖先。

**归纳**：假设 $\mathtt{fa}[\cdot][k - 1]$ 正确给出 $2^{k-1}$ 级祖先。则：

$$\mathtt{fa}[u][k] = \mathtt{fa}[\mathtt{fa}[u][k-1]][k-1]$$

含义是——从 $u$ 跳 $2^{k-1}$ 步到祖先 $w$，再从 $w$ 跳 $2^{k-1}$ 步——总共跳 $2^k$ 步。所以 $\mathtt{fa}[u][k]$ 是 $u$ 的 $2^k$ 级祖先。$\blacksquare$

### 任意步数的可达性

**命题**：从 $u$ 出发用倍增跳到任意 $d$ 级祖先（$d \ge 0$）只需 $O(\log d)$ 步。

**证明**：把 $d$ 写成二进制 $d = \sum_{k} 2^{k_i}$（每个 $k_i$ 不同）。依次对每个 $k_i$ 用 $\mathtt{fa}[\cdot][k_i]$ 跳跃，到达 $d$ 级祖先。二进制位数 $\le \log_2 d + 1 = O(\log d)$。$\blacksquare$

### 同深度后同步上跳的正确性

**命题**：当 $u, v$ 同深度且 $u \ne v$ 时，从大到小尝试 $k = \log_n, \ldots, 0$ 同步上跳 $2^k$ 步（仅当 $\mathtt{fa}[u][k] \ne \mathtt{fa}[v][k]$ 时跳）的过程结束后，$\mathtt{fa}[u][0] = \mathrm{lca}(u, v)$。

**证明**：

**关键观察**：在过程中始终保持不变量——"$u, v$ 同深度，且 $u \ne v$"。

**归纳**：每次循环考察 $k$（从大到小）：

- 若 $\mathtt{fa}[u][k] = \mathtt{fa}[v][k]$：意味着 $u, v$ 的 $2^k$ 级祖先相同，即 $\mathrm{lca}(u, v)$ 在 $u, v$ 的 $2^k$ 级祖先**或更近**——不能跳，跳了会越过 LCA

- 若 $\mathtt{fa}[u][k] \ne \mathtt{fa}[v][k]$：$\mathrm{lca}(u, v)$ 在 $u, v$ 的 $2^k$ 级祖先**之上**——可以放心跳 $2^k$ 步

**贪心从大到小试是对的**：每次跳能跳的最大步数。最终 LCA 与当前 $u, v$ 的距离 $< 2^0 = 1$，但仍 $> 0$（因为 $u \ne v$）——所以 LCA 距离 = 1，即 $\mathtt{fa}[u][0] = \mathrm{lca}(u, v)$。

**为什么不会跳过 LCA**：若某次跳后 $\mathtt{fa}[u][k] = \mathtt{fa}[v][k]$，意味着跳过头了——但算法的判断 `fa[u][k] != fa[v][k]` 保证只在"跳后还不相同"时才跳，所以不会越过。$\blacksquare$

### 第一阶段（统一深度）的正确性

把 $u$ 上跳 $\mathtt{depth}[u] - \mathtt{depth}[v]$ 步后到达深度 $\mathtt{depth}[v]$。倍增展开二进制位逐次跳。若 $u$ 上跳后 $u = v$，说明 $v$ 是 $u$ 的祖先，$\mathrm{lca}(u, v) = v$。$\blacksquare$

### 复杂度的来源

预处理 DFS $O(n)$ + 每个节点填 $\log n$ 个 $\mathtt{fa}$ = $O(n \log n)$。

单次查询：第一阶段最多 $\log n$ 次跳跃，第二阶段最多 $\log n$ 次循环——共 $O(\log n)$。$\blacksquare$

## 与其他 LCA 算法的对比

| 算法                 | 预处理                | 单次查询                | 备注                   |
| ------------------ | ------------------ | ------------------- | -------------------- |
| 倍增法                | $O(n \log n)$      | $O(\log n)$         | 在线，最常用               |
| 欧拉序 + ST 表         | $O(n \log n)$      | $O(1)$              | 在线，查询最快但常数大          |
| Tarjan 离线          | $O(n + q)$         | 总计 $O(\alpha(n) q)$ | 离线，适合查询数 $q$ 已知      |
| 树链剖分               | $O(n)$             | $O(\log n)$         | 已剖分时顺手用              |

**经验**：单次问题查询 → 倍增（写起来最快）；查询多到极限 → 欧拉序 + ST 表；离线题 → Tarjan。

## 应用：树上路径问题三件套

LCA 的最大用途之一是把"两点路径"问题分解为"根到点"问题——

**1. 路径长度**：$\mathtt{dist}(u, v) = \mathtt{depth}[u] + \mathtt{depth}[v] - 2 \cdot \mathtt{depth}[\mathrm{lca}]$

**2. 路径权值和**（用 [[树上前缀和与差分]]）：设 $\mathtt{sum}[u]$ 为根到 $u$ 的路径权和，则

$$\sum_{e \in \mathtt{path}(u, v)} w(e) = \mathtt{sum}[u] + \mathtt{sum}[v] - 2 \cdot \mathtt{sum}[\mathrm{lca}]$$

**3. 路径最值**：在倍增数组同时维护"$u$ 到其 $2^k$ 级祖先路径上的最大值 / 最小值"，查询时一并合并。

## 相关例题

- [洛谷P3379 【模板】最近公共祖先（LCA）](https://www.luogu.com.cn/problem/P3379)

- [洛谷P1967 [NOIP2013 提高组] 货车运输](https://www.luogu.com.cn/problem/P1967)