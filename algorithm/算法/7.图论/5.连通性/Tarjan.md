#难度/★★★★

> 一遍 DFS 配合 `dfn` / `low` 时间戳和栈，$O(n + m)$ 求出有向图的所有强连通分量。

## 前置知识

- [[DFS]]

- [[栈]]

## 核心思想

**强连通分量（Strongly Connected Component, SCC）**：有向图 $G$ 的极大子图，使得子图中任意两点 $u, v$ 都互相可达（既存在 $u \to v$ 路径，也存在 $v \to u$ 路径）。

整张有向图可以唯一地划分为若干 SCC（每个节点恰属于一个 SCC）。把每个 SCC 缩成一个点，得到的"缩点图"必为 DAG——这是图论中的经典结构。

> 注：算法竞赛中"Tarjan 算法"通常默认指**求 SCC** 的版本。Tarjan 也用同样的 dfn / low 框架求 [[割点与桥]] 和 [[LCA]]，但这里专讲 SCC。

**Tarjan 算法的核心**——用一遍 DFS + 一个辅助栈，定义两个时间戳：

- $\mathtt{dfn}[u]$：$u$ 的**DFS 序**（被首次访问的时间戳，从 1 开始递增）

- $\mathtt{low}[u]$：$u$ 的子树中，通过任意边（含返祖边和横叉边）能到达的**最小 dfn 值**

DFS 过程中维护一个栈，存放"已访问但所属 SCC 尚未确定"的节点。当 DFS 完成 $u$（即将从递归栈弹出 $u$）时若发现 $\mathtt{dfn}[u] = \mathtt{low}[u]$——意味着 $u$ 的子树无法到达比 $u$ 更早的节点——则 $u$ 是某个 SCC 的"DFS 树根"，把栈中 $u$ 之上的所有节点连同 $u$ 一起弹出，构成一个 SCC。

**为什么这个判定是对的**？$\mathtt{dfn}[u] = \mathtt{low}[u]$ 时 $u$ 的子树自成一个"封闭世界"——既不能向更早的祖先发出反向边（否则 low 会更小），那些"在栈中、由 $u$ 子树进入"的节点也只能在该子树内闭合形成 SCC。详见正确性证明。

## 适用场景

- **求强连通分量**（最经典应用）

- **缩点**：把 SCC 缩成点后变 DAG，用于：

  - 在 DAG 上做 dp（如最长路、计数）

  - 与 [[拓扑排序]] 联用解决"必须按依赖访问"的有向图问题

- **2-SAT 问题**：变量与子句关系建图，SCC 缩点后判可满足性

- **环检测**：图含环 $\Leftrightarrow$ 至少一个 SCC 大小 $> 1$（自环也算）

- 不适用：无向图（应用 [[割点与桥]] 或并查集）；只问连通性而不需要 SCC 结构（用 [[BFS]] / [[DFS]] 即可）

## 步骤拆解

1. 初始化：$\mathtt{dfn}[u] = \mathtt{low}[u] = 0$，$\mathtt{in\_stack}[u] = \mathtt{false}$，$\mathtt{timer} = 0$

2. 对每个 $\mathtt{dfn}[u] = 0$ 的节点调用 $\mathtt{dfs}(u)$

3. $\mathtt{dfs}(u)$：

   a. $\mathtt{timer} \mathrel{+}= 1$；$\mathtt{dfn}[u] = \mathtt{low}[u] = \mathtt{timer}$

   b. 把 $u$ 压入栈，$\mathtt{in\_stack}[u] = \mathtt{true}$

   c. 枚举每条出边 $(u, v)$：

     - 若 $\mathtt{dfn}[v] = 0$：递归 $\mathtt{dfs}(v)$，回溯后用 $\mathtt{low}[v]$ 更新 $\mathtt{low}[u]$

     - 若 $v$ 在栈中（$\mathtt{in\_stack}[v]$）：$\mathtt{low}[u] = \min(\mathtt{low}[u], \mathtt{dfn}[v])$

     - 若 $v$ 已访问但不在栈中：跳过（$v$ 已属其他 SCC）

   d. 若 $\mathtt{dfn}[u] = \mathtt{low}[u]$：弹出栈顶直到弹出 $u$ 自己，这些节点构成一个 SCC

## 代码模板

```cpp
class tarjan_scc {

private:

    int n;

    vector<vector<int>> g;

    vector<int> dfn, low, scc_id;

    vector<bool> in_stack;

    stack<int> stk;

    int timer, scc_cnt;

    void dfs(int u) {

        timer += 1;

        dfn[u] = low[u] = timer;

        stk.push(u);

        in_stack[u] = true;

        for (int v : g[u]) {

            if (dfn[v] == 0) {

                dfs(v);

                low[u] = min(low[u], low[v]);

            } else if (in_stack[v]) {

                low[u] = min(low[u], dfn[v]);

            }

            // 若 v 已访问且不在栈中，跳过

        }

        if (dfn[u] == low[u]) {

            scc_cnt += 1;

            int v;

            do {

                v = stk.top();

                stk.pop();

                in_stack[v] = false;

                scc_id[v] = scc_cnt;

            } while (v != u);

        }

    }

public:

    tarjan_scc(int total, vector<vector<int>>& g_in) {

        n = total;

        g = g_in;

    }

    // 返回 scc_id 数组（同一 SCC 的节点 id 相同），以及 SCC 总数
    pair<vector<int>, int> solve() {

        dfn.assign(n + 1, 0);

        low.assign(n + 1, 0);

        scc_id.assign(n + 1, 0);

        in_stack.assign(n + 1, false);

        timer = 0;

        scc_cnt = 0;

        for (int u = 1; u <= n; u++) {

            if (dfn[u] == 0) {

                dfs(u);

            }

        }

        return {scc_id, scc_cnt};

    }

};
```

> 💡 **`in_stack` 判断的关键性**：DFS 过程中遇到已访问的 $v$ 有两种情况——

> - $v$ 仍在栈中：$v$ 是 $u$ 的某个祖先（或祖先的兄弟分支但同 SCC），用 $\mathtt{dfn}[v]$ 更新 $\mathtt{low}[u]$

> - $v$ 不在栈中：$v$ 已属于先前关闭的某个 SCC——它和 $u$ 已不在同一 SCC（否则 $u$ 应该和 $v$ 一起被弹出）。**不更新 $\mathtt{low}[u]$**

> 💡 **缩点应用**：得到 `scc_id[]` 后，可以构建缩点图——枚举原图每条边 $(u, v)$，若 `scc_id[u] != scc_id[v]` 则在缩点图中加边 `scc_id[u] -> scc_id[v]`（注意去重）。缩点图必为 DAG，可用 [[拓扑排序]] 进一步处理。

> ⚠️ **递归深度**：图很大时 DFS 可能爆栈（$n > 10^5$ 时风险）。可改写成显式栈的迭代版本，但代码复杂得多。

## 复杂度分析

- 时间复杂度：$O(n + m)$，每个节点和每条边各被访问一次

- 空间复杂度：$O(n + m)$

## 正确性证明

### dfn / low 的语义

**$\mathtt{dfn}[u]$**：$u$ 的 DFS 访问顺序，全图唯一。

**$\mathtt{low}[u]$**：$u$ 的子树中（包括 $u$ 自己），通过**至多一条返祖边或横叉边**能到达的节点中，最小的 $\mathtt{dfn}$ 值——前提是该节点目前仍在栈中。

更准确地：$\mathtt{low}[u]$ 是 $u$ 子树中的某节点 $w$ 的 $\mathtt{dfn}[w]$，使得存在路径 $u \to \cdots \to v \to w$，其中 $v$ 是 $u$ 子树中的节点，$w$ 仍在栈中。

### 关键引理：栈中节点的语义

**引理 1**：DFS 过程中，栈中的节点恰好是"已访问但所属 SCC 尚未确定"的节点。

**证明**：节点入栈发生在 $\mathtt{dfn}$ 设置时（首次访问）；出栈发生在 $\mathtt{dfn}[u] = \mathtt{low}[u]$ 触发的弹栈操作中——这正是 SCC 被确认的时刻。$\blacksquare$

**引理 2**：栈中节点形成一个 DFS 路径上的"延伸"——更准确地，栈底是当前 DFS 路径上某个最早的节点。栈中所有节点在某种意义下都"互相可达 / 同 SCC 候选"。

### dfn[u] = low[u] 是 SCC 根的判定

**核心命题**：当 DFS 完成 $u$ 时，若 $\mathtt{dfn}[u] = \mathtt{low}[u]$，则栈中 $u$ 及其上的所有节点构成一个 SCC，且 $u$ 是这个 SCC 中 dfn 最小的节点（即"DFS 树意义下的根"）。

**证明分两部分**：

**(1) 这些节点确实属于同一 SCC**

设栈中 $u$ 之上的节点（含 $u$）为 $u = w_0, w_1, \ldots, w_k$（按入栈顺序），它们的 dfn 满足 $\mathtt{dfn}[u] < \mathtt{dfn}[w_1] < \cdots < \mathtt{dfn}[w_k]$。

每个 $w_i$（$i \ge 1$）都是 $u$ 的子孙节点（在 DFS 树中）——因为 $w_i$ 在 $u$ 之后入栈，且 $u$ 在 $w_i$ 出栈前没有退出递归。所以 $u \to^* w_i$（顺着 DFS 树即可）。

由 $\mathtt{low}[w_i] \le \mathtt{dfn}[u]$（否则 $\mathtt{low}[u]$ 会被 $\mathtt{low}[w_i]$ 拉小，与 $\mathtt{dfn}[u] = \mathtt{low}[u]$ 矛盾——除非 $w_i$ 的 low 路径绕到栈外，但栈外节点已属其他 SCC，与 $w_i$ 在栈中矛盾）——所以从 $w_i$ 出发能到达某个 dfn $\le \mathtt{dfn}[u]$ 的栈中节点 $w'$，再由 DFS 树关系 $w' \to^* u$（$w'$ 是 $u$ 的祖先或 $u$ 自己），合起来 $w_i \to^* u$。

所以 $u$ 与每个 $w_i$ 互达——它们在同一 SCC。

**(2) 这些节点构成完整的 SCC**

反证：假设存在与 $u$ 同 SCC 的节点 $w$ 不在 $u$ 之上的栈段中。两种情况：

- $w$ 已出栈（属于先前关闭的 SCC）：那么 $w$ 已在那个 SCC 中——但 $u$ 与 $w$ 同 SCC，$u$ 也应在那个 SCC 中。矛盾于 $u$ 现在才被关闭。

- $w$ 尚未访问：但 $u \to^* w$，DFS 从 $u$ 出发能到达 $w$——按 DFS 流程 $w$ 应早已被访问。矛盾。

所以 $u$ 之上的栈段恰好是 $u$ 的整个 SCC。$\blacksquare$

### 算法的完整性

每个节点被访问一次（DFS 完备性），每个节点入栈一次出栈一次。当算法终止时所有节点都已确定 $\mathtt{scc\_id}$——SCC 划分完整。$\blacksquare$

### 复杂度的来源

每个节点 DFS 一次（入栈、出栈），每条边检查一次。所有操作均摊 $O(1)$，总计 $O(n + m)$。$\blacksquare$

## 与缩点 + DAG 的联用

Tarjan 求出 SCC 后的标准操作——

```cpp

// 1. Tarjan 求 SCC，得 scc_id[]

// 2. 构建缩点图

vector<vector<int>> dag(scc_cnt + 1);

for (int u = 1; u <= n; u++) {

    for (int v : g[u]) {

        if (scc_id[u] != scc_id[v]) {

            dag[scc_id[u]].push_back(scc_id[v]);

        }

    }

}

// 3. 在 DAG 上跑拓扑排序、dp、最长路等

```

**Tarjan 输出的 SCC 编号有个有用的性质**：scc_id 的值越小，对应的 SCC 在缩点图中越靠后（拓扑序逆序）。这意味着遍历 `scc_id` 从大到小已经是 DAG 的**逆拓扑序**，省去一次拓扑排序。

## 与其他求 SCC 算法的对比

| 算法            | 复杂度         | DFS 次数  | 备注                 |
| ------------- | ----------- | ------- | ------------------ |
| Tarjan        | $O(n + m)$  | 1 次     | 主流，dfn/low 需理解     |
| Kosaraju      | $O(n + m)$  | 2 次     | 反图 + 顺逆 DFS，更直观    |
| Gabow         | $O(n + m)$  | 1 次     | 用两个栈，理论上常数小        |

**经验**：竞赛中 Tarjan 用得最多——一次 DFS、代码紧凑，且与 [[割点与桥]] 共用同样的 dfn/low 框架。

## 相关例题

- [洛谷B3609 【模板】强连通分量](https://www.luogu.com.cn/problem/B3609)

- [洛谷P3387 【模板】缩点](https://www.luogu.com.cn/problem/P3387)

- [洛谷P4782 【模板】2-SAT](https://www.luogu.com.cn/problem/P4782)

$\blacksquare$