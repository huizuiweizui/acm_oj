#难度/★★

> 一种"一条路走到黑，走不通再回头"的搜索策略，用递归或栈实现，是树/图遍历与暴力枚举的基石。

## 核心思想

DFS（Depth-First Search，深度优先搜索）的核心是**沿着一个分支一直深入**，直到无路可走（叶子节点 / 已访问 / 无可行后继）才**回溯**到上一个分叉点尝试另一条路。整个过程的执行顺序对应着对搜索树的**前序遍历**。

DFS 有两种典型用法：

- **遍历型**：访问图 / 树中所有节点，每个点只访问一次（用 `visited[]` 数组防重复），适合判断连通性、求连通分量等

- **枚举型（回溯）**：枚举所有可行的"决策序列"，一次只决定一步，递归处理后**撤销**该步决策，恢复现场。八皇后、全排列、子集和都是这种

DFS 的实现几乎总是用**递归**——隐式利用系统调用栈，写起来比手写栈简洁许多。

## 适用场景

- 图 / 树的遍历，判断连通性、求连通分量

- 枚举所有方案（八皇后、全排列、子集、组合等）

- 求树上路径、子树信息（一次 DFS 就能完成 [[树形dp]] 或 [[树上前缀和与差分]]）

- [[拓扑排序]] 的递归版本

- 配合剪枝可解中等规模的搜索题（[[迭代加深]] / [[A∗]] 都是 DFS 的进化）

- 不适用：求**最短路径 / 步数**（DFS 找到的不是最短解，应用 [[BFS]]）；状态空间过大且无明显剪枝（会TLE）

## 步骤拆解

**遍历型 DFS 框架**：

1. 维护 `visited[]` 数组，访问一个点前先检查是否已访问

2. 进入函数：标记当前点为已访问，处理它

3. 递归访问所有未访问的邻居

4. （遍历型不需要回溯——访问标记不撤销）

**枚举型 DFS（回溯）框架**：

1. 维护"当前已做的决策"和"当前状态"

2. 进入函数：判断是否到达终点（输出答案 / 更新最优值）

3. 枚举下一步所有可能的选择

4. 对每个选择：**修改状态 → 递归 → 撤销修改**（恢复现场，让上层枚举其他选择）

## 代码模板

**模板一：图的 DFS 遍历（求连通分量个数）**

```cpp
class graph_dfs {

private:

    int n;

    vector<vector<int>> g;

    vector<bool> visited;

    void dfs(int u) {

        visited[u] = true;

        for (int v : g[u]) {

            if (!visited[v]) {

                dfs(v);

            }

        }

    }

public:

    graph_dfs(int total, vector<vector<int>>& g_in) {

        n = total;

        g = g_in;

        visited.resize(n + 1, false);

    }

    int count_components() {

        int cnt = 0;

        for (int i = 1; i <= n; i++) {

            if (!visited[i]) {

                dfs(i);

                cnt += 1;

            }

        }

        return cnt;

    }

};
```

**模板二：枚举型 DFS（八皇后）**

```cpp
class n_queens {

private:

    int n;

    int total;                          // 方案数

    vector<int> col;                    // col[r] = 第 r 行皇后所在列

    vector<bool> used_col, used_diag1, used_diag2;

    void dfs(int r) {

        if (r > n) {

            total += 1;

            return;

        }

        for (int c = 1; c <= n; c++) {

            int d1 = r - c + n;         // 主对角线编号

            int d2 = r + c;             // 副对角线编号

            if (used_col[c] || used_diag1[d1] || used_diag2[d2]) {

                continue;

            }

            // 1. 修改状态

            col[r] = c;

            used_col[c] = true;

            used_diag1[d1] = true;

            used_diag2[d2] = true;

            // 2. 递归

            dfs(r + 1);

            // 3. 撤销修改

            used_col[c] = false;

            used_diag1[d1] = false;

            used_diag2[d2] = false;

        }

    }

public:

    n_queens(int size) {

        n = size;

        total = 0;

        col.resize(n + 1, 0);

        used_col.resize(n + 1, false);

        used_diag1.resize(2 * n + 1, false);

        used_diag2.resize(2 * n + 1, false);

    }

    int solve() {

        dfs(1);

        return total;

    }

};
```

> 💡 **回溯三步曲**：**修改状态** → **递归** → **撤销修改**。三步缺一不可——不修改无法约束子问题，不撤销会污染兄弟分支。
  
**模板三：树的 DFS（求子树大小）**

```cpp
class subtree_size {

private:

    int n;

    vector<vector<int>> g;

    vector<int> sz;                     // sz[u] = 以 u 为根的子树大小

    void dfs(int u, int fa) {

        sz[u] = 1;

        for (int v : g[u]) {

            if (v != fa) {

                dfs(v, u);

                sz[u] += sz[v];

            }

        }

    }

public:

    subtree_size(int total, vector<vector<int>>& g_in, int root) {

        n = total;

        g = g_in;

        sz.resize(n + 1, 0);

        dfs(root, 0);

    }

    int get(int u) {

        return sz[u];

    }

};
```

> 💡 **树上 DFS 不需要 visited**：用 `fa` 参数记住父节点，递归时跳过即可，比维护 `visited[]` 更简洁。

## 复杂度分析
- 时间复杂度：

	- 遍历型 DFS：$O(n + m)$（$n$ 节点数，$m$ 边数）
	
	- 枚举型 DFS：取决于剪枝效率，最坏 $O(b^d)$，实际远小于此

- 空间复杂度：$O(n)$（递归栈深度）+ 状态数组

## 正确性证明

### 遍历型 DFS 的完备性

**命题**：从起点 $s$ 出发的 DFS 能且仅能访问到 $s$ 所在连通分量的所有节点，每个节点恰好一次。

**证明（不漏）**：用归纳法证明"$s$ 可达的节点都会被访问"。

设 $u$ 是从 $s$ 可达的节点，存在路径 $s = v_0 \to v_1 \to \cdots \to v_k = u$。

- $v_0 = s$ 在 DFS 入口被立即访问。

- 假设 $v_i$ 已被访问（在某次 $\mathtt{dfs}(v_i)$ 调用中），则进入 $v_i$ 时一定会枚举其所有邻居。$v_{i+1}$ 是 $v_i$ 的邻居：

  - 若 $v_{i+1}$ 此前未访问，则在该枚举中触发 $\mathtt{dfs}(v_{i+1})$，被访问

  - 若 $v_{i+1}$ 已访问，结论也成立

由归纳，$v_k = u$ 必然被访问。$\blacksquare$

**证明（不重）**：访问前的 `if (!visited[v])` 判断保证已访问的节点不会被再次进入函数，所以每个节点恰好访问一次。

**证明（仅限连通分量）**：未与 $s$ 连通的节点不存在通往它的边链——递归过程中无法到达。

### 枚举型 DFS（回溯）的完备性

**命题**：对决策树（每个节点有若干分支）做回溯型 DFS，能且仅能枚举所有合法的"决策序列"。

**证明**：

**完备性（所有合法序列都被枚举到）**：考虑任一合法序列 $\sigma = (c_1, c_2, \ldots, c_d)$。在 DFS 第 $i$ 层，由于 `for` 循环枚举该层所有可能的 $c$，必然枚举到 $c_i$（前提：前 $i-1$ 步选择 $c_1, \ldots, c_{i-1}$ 后 $c_i$ 仍合法，这正是"$\sigma$ 合法"的含义）。归纳到第 $d$ 层即枚举出 $\sigma$。

**正确性（每次到达终点的状态都对应合法序列）**：每次 `dfs(d+1)` 触发时，前 $d$ 步选择都通过了对应的合法性检查（由 `if (!used_col[c] || ...) continue;` 这种条件保证），所以输出的状态合法。

**不重复**：枚举顺序由 `for` 循环固定，每个分支只走一次——但**注意**：不同的中间分支可能导向相同的最终状态。若题目要求"不重复方案"，需要在算法层面去重（如限定字典序）。$\blacksquare$

### 撤销修改的必要性

**命题**：枚举型 DFS 中，递归返回后必须撤销当前层的修改，否则结果错误。

**反证**：假设不撤销 `used_col[c] = true`，则递归返回后 `c` 仍被标记为占用——同层后续枚举其他列时，本可放置但被误判禁用，导致漏掉合法分支。

形式化地，回溯算法的循环不变量是——"每次 `for` 循环新一轮迭代开始时，状态等于函数入口时的状态"。撤销修改是保持这个不变量的唯一手段。$\blacksquare$

### 复杂度的来源

- **遍历型**：每个节点访问 $O(1)$ 次，每条边检查 $O(1)$ 次，总计 $O(n + m)$。

- **枚举型**：搜索树深度 $d$，每节点分支 $b$，节点总数 $\le \frac{b^{d+1} - 1}{b - 1} = O(b^d)$。剪枝把分支因子有效降低，所以剪枝是回溯算法的命脉。

**剪枝的力量**：朴素 DFS 的复杂度往往是指数级，但好的剪枝能让搜索树砍掉绝大多数分支。八皇后用 `used_col / used_diag` 提前过滤就是一种剪枝。常见剪枝方式：可行性剪枝（明显不可行就 return）、最优性剪枝（已超过当前最优解就 return）、对称性剪枝（避免重复计算等价分支）。

## 相关例题

- [洛谷P1219 八皇后](https://www.luogu.com.cn/problem/P1219)

- [洛谷P1019 单词接龙](https://www.luogu.com.cn/problem/P1019)