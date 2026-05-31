#难度/★★★

> 在树上做 dp——状态以节点为下标，转移**自底向上**通过 DFS 后序完成。它是 [[线性dp]] 从"序列"扩展到"树"的自然结果，也是 [[状态机dp]] 在树上的常见载体。

## 前置知识

- [[DFS]]

- [[线性dp]]

## 核心思想

线性 dp 的状态沿"数组下标 $i$"推进——但**树**这种结构没有线性顺序，怎么定义状态的推进方向？

答案藏在树的结构里——每个非根节点都有**唯一的父节点**，所以"父→子"形成有向关系。把这个关系反过来——**子→父**——就给出了天然的 dp 推进方向：**叶子先算、根最后算**。

**树形 dp 通用框架**：

- **状态**：$f[u]$（或 $f[u][\text{state}]$）表示"以 $u$ 为根的子树中，某种最优值 / 计数"

- **转移**：$f[u]$ 由所有子节点 $v$ 的 $f[v]$ 合并而来——具体合并规则取决于题意

- **遍历顺序**：DFS 后序——先递归处理所有子节点、再合并算出当前节点

- **答案**：通常是 $f[\text{root}]$ 或 $\max / \min$ 某个节点上的值

> 💡 **DFS 后序天然保证子节点先算**：递归到一个节点时，先走完所有子节点的递归再回到本节点处理 $f$——这就是树形 dp 自底向上的实现方式。完全不需要像 [[区间dp]] 那样精心设计循环顺序。

## 经典模型：没有上司的舞会

> $n$ 个职员组成一个**树形**上下级结构（除老板外每人有唯一直接上司）。第 $u$ 个职员的"快乐值"为 $a_u$。每个职员只在"自己的直接上司**不来**"的情况下才愿意参加舞会。问邀请哪些人使总快乐值最大。

**状态怎么想**：约束是"父子不能同时来"——和 [[状态机dp]] 中的打家劫舍如出一辙！所以"$u$ 节点来不来"必须显式纳入状态。

定义两个状态——

- $f[u][0] =$ $u$ **不来**时，以 $u$ 为根子树的最大总快乐值

- $f[u][1] =$ $u$ **来**时，以 $u$ 为根子树的最大总快乐值

这个状态有最优子结构（大子树的最优来自各子节点子树的最优）与无后效性（$f[u]$ 只依赖各 $f[v]$，与 $u$ 的祖先无关）。

**转移怎么推**：考察 $u$ 的每个子节点 $v$ 与 $u$ 的约束——

- **$u$ 不来时**（$f[u][0]$）：每个子节点 $v$ 来或不来都合法，独立取较优——$\sum_v \max(f[v][0],\, f[v][1])$

- **$u$ 来时**（$f[u][1]$）：每个子节点 $v$ **必须不来**——$\sum_v f[v][0]$，再加上 $u$ 自己的 $a_u$

合写——

$$f[u][0] = \sum_{v \in \text{children}(u)} \max(f[v][0],\, f[v][1])$$

$$f[u][1] = a_u + \sum_{v \in \text{children}(u)} f[v][0]$$

**边界**：叶子 $u$（无子节点）的 $f[u][0] = 0$、$f[u][1] = a_u$——上面公式中 $\sum$ 为空时取 0，自然涵盖。

**答案**：$\max(f[\text{root}][0],\, f[\text{root}][1])$。

> 💡 **本质就是打家劫舍的树上版本**：父子不能同选 + 子树独立合并 = "树上最大权独立集"。线性版的两状态、转移结构完全保留——只是把"前一间"换成"所有子节点"再求和。

## 适用场景

- 树形约束下的最优化 / 计数：选点 / 选边 / 染色 / 路径

- 经典模型：树上最大权独立集（没有上司的舞会）、树的直径与重心、子树统计

- 状态机 + 树（如选与不选、染色限制相邻）→ 在每个节点维护多种"机器状态"

- 限制 $\le$ 一个常数的"挑选 $k$ 个"问题 → 见 [[树上背包]]

- 求"每个节点为根时的某值"→ 见 [[换根dp]]

- 不适用：图有环（不是树）；状态依赖跨越非父子关系

## 步骤拆解

1. **建邻接表**：根据题意建有根树（直接给父子关系）或无根树（双向边、需要钦定根）

2. **设状态**：$f[u]$ 或 $f[u][\text{state}]$，含义清晰到能写出转移

3. **写 DFS**：递归子节点 → 把子节点的 $f$ 合并到自己

4. **边界**：叶子节点的 $f$ 通常是平凡值（0、$a_u$ 等），代码中由"$\sum$ 为空"自然处理

5. **答案**：从 $f[\text{root}]$ 中提取（或在 DFS 过程中用全局变量收集，如树的直径）

## 代码模板

**模板一：没有上司的舞会（有根树）**

```cpp

class no_boss_dance {

private:

    int n;

    int root;

    vector<vector<int>> children;                   // children[u] = u 的子节点

    vector<long long> happiness;                    // 1-indexed

    vector<vector<long long>> f;                    // f[u][0/1]

    void dfs(int u) {

        f[u][0] = 0;

        f[u][1] = happiness[u];

        for (int v : children[u]) {

            dfs(v);

            f[u][0] += max(f[v][0], f[v][1]);

            f[u][1] += f[v][0];

        }

    }

public:

    no_boss_dance(int n_in, int root_in,

                  const vector<vector<int>>& children_in,

                  const vector<long long>& happiness_in) {

        n = n_in;

        root = root_in;

        children = children_in;

        happiness = happiness_in;

        f.assign(n + 1, vector<long long>(2, 0));

    }

    long long solve() {

        dfs(root);

        return max(f[root][0], f[root][1]);

    }

};
```

**模板二：无根树通用框架（用 $\mathtt{fa}$ 避免回头）**

无根树时邻接表存双向边，DFS 传 $\mathtt{fa}$ 参数避免回到父节点——这是 [[DFS]] 中树上 DFS 的标准写法：

```cpp
void dfs(int u, int fa) {

    // 初始化 f[u]

    for (int v : g[u]) {

        if (v == fa) continue;                      // 跳过父节点

        dfs(v, u);

        // 用 f[v] 更新 f[u]

    }

}

// 调用：dfs(root, 0);   // 0 是虚拟父节点

```

## 复杂度分析

- 时间复杂度：$O(n)$——每个节点的转移是 $O(\deg(u))$，所有节点之和为 $O(n + m) = O(n)$（树有 $n - 1$ 条边）

- 空间复杂度：$O(n)$（$f$ 数组 + DFS 递归栈）

> ⚠️ **递归深度**：若树退化成链（如以下标 1 为根的链 $1 \to 2 \to \cdots \to n$），递归深度可达 $n$。$n \ge 10^5$ 时要么开大栈空间，要么把递归改写成手写栈的迭代版本。

## 正确性证明

### 最优子结构

**命题**：以 $u$ 为根的子树最优解（指定 $u$ 来或不来时的最大快乐值）等于各子节点 $v$ 对应子树的最优解之和（加上 $u$ 自身可能的快乐值）。

**证明**：以 $u$ 来的情形 $f[u][1]$ 为例。最优方案在 $u$ 子树中选了一些节点 $S$，$u \in S$。对每个子节点 $v$——

- $v \notin S$（因 $u \in S$ 强制 $v \notin S$）

- $v$ 子树中选的部分 $S_v = S \cap V(\text{subtree}(v))$ 是合法（无父子相邻）的选择

由 $f[v][0]$ 的定义（$v$ 不在时 $v$ 子树最优），$\sum_{u' \in S_v} a_{u'} \le f[v][0]$。

整体快乐值 $= a_u + \sum_v \sum_{u' \in S_v} a_{u'} \le a_u + \sum_v f[v][0]$。等号在每个 $S_v$ 都取到 $f[v][0]$ 对应方案时达到。$\blacksquare$

### 无后效性

**命题**：$f[u]$ 只依赖 $u$ 子树内的信息，不依赖 $u$ 的祖先或兄弟子树。

**证明**：转移方程 $f[u][\cdot] = \cdots + \sum_v f[v][\cdot]$ 中只读取子节点的 $f$。子节点的 $f$ 又只读取它们的子节点的 $f$——由归纳，整个 $f[u]$ 的计算只涉及 $u$ 子树内的节点。$\blacksquare$

## 应用扩展

### 应用一：树的直径（最长路径）

> 给一棵 $n$ 个节点、带边权的无根树，求树上**任意两点间最长简单路径**的总边权。

**状态**：$g[u] =$ 从 $u$ 出发往**子树内**走的最长路径长度。

转移——

$$g[u] = \max\left(0,\, \max_{v \in \text{children}(u)} (g[v] + w(u, v))\right)$$

**关键观察**：树的最长路径必然有一个"最高点" $u$——路径形如"从 $u$ 子树内一点经 $u$ 到子树内另一点"，由 $u$ 的两条**最长**与**次长**向下路径拼接而成。

所以在 DFS 中对每个 $u$ 记录其子节点 $v$ 中 $g[v] + w(u, v)$ 的最大值（$\mathtt{longest}$）与次大值（$\mathtt{second}$），全局最长路径 = $\max_u (\mathtt{longest} + \mathtt{second})$。

```cpp

class tree_diameter {

private:

    int n;

    vector<vector<pair<int, long long>>> g_;        // g_[u] = {(v, w)}

    long long ans;

    long long dfs(int u, int fa) {

        long long longest = 0, second = 0;          // 第一长、次长向下路径

        for (auto [v, w] : g_[u]) {

            if (v == fa) continue;

            long long down = dfs(v, u) + w;

            if (down > longest) {

                second = longest;

                longest = down;

            } else if (down > second) {

                second = down;

            }

        }

        ans = max(ans, longest + second);

        return longest;                           // 只返回"向下"，由父节点决定后续拼接

    }

public:

    tree_diameter(int n_in,

                  const vector<vector<pair<int, long long>>>& g_in) {

        n = n_in;

        g_ = g_in;

    }

    long long solve(int root) {

        ans = 0;

        dfs(root, 0);

        return ans;

    }

};
```

> 💡 **DFS 返回值的语义**：`dfs(u, fa)` **返回**给父节点的是 $g[u]$（即从 $u$ 出发向子树内的最长路径），而把"过 $u$ 的最长路径长度"**写进全局 `ans`**。两种数据用不同方式输出，非常典型的树形 dp 写法。

详细见 [[树的直径]]（图论模块）。

### 应用二：树形 + 状态机

很多题中节点有多个"机器状态"——例如染色限制相邻不同色——可以参考 [[状态机dp]] 的思路在每个节点维护 $f[u][\text{state}]$ 数组，转移时对每个 $v$ 枚举其状态。

例如树上三色染色问题（相邻不同色）——

$$f[u][k] = \sum_v \min_{k' \ne k} f[v][k']$$

（$k, k' \in \{0, 1, 2\}$ 是颜色编号）

## 几个常见错误

- **无根树漏传 `fa` 参数**：双向边时会无限递归。务必在 DFS 中跳过 $v = fa$

- **从子节点初始化的位置不对**：$f[u][0]$、$f[u][1]$ 的初值（$0$、$a_u$）必须在合并子节点的循环**之前**设好；很多人在循环里反复重置导致 bug

- **`children` vs `g`**：有根树用 `children`（单向，无需 `fa`）；无根树用 `g`（双向，需 `fa`）。两者不可混用

- **递归栈溢出**：$n \ge 10^5$ 且树退化成链时栈深超过默认值——竞赛中要么设栈大小、要么改迭代

## 相关例题

- [洛谷P1352 [HAOI2009] 没有上司的舞会](https://www.luogu.com.cn/problem/P1352)

- [洛谷P1273 有线电视网](https://www.luogu.com.cn/problem/P1273)

- [洛谷P2014 [CTSC1997] 选课](https://www.luogu.com.cn/problem/P2014)

- [洛谷P1131 [ZJOI2007] 时态同步](https://www.luogu.com.cn/problem/P1131)

- [洛谷P2585 [ZJOI2006] 三色二叉树](https://www.luogu.com.cn/problem/P2585)

- [洛谷P1352 没有上司的舞会](https://www.luogu.com.cn/problem/P1352)