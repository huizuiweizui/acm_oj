#难度/★★★★★

> [[KMP]] 在 [[Trie]] 上的推广——多模式匹配的标准利器，把 $k$ 个模式串建成 Trie 后用 fail 指针把"失配回跳"转化为 $O(1)$ 转移。

## 前置知识

- [[KMP]]

- [[Trie]]

- [[BFS]]

## 核心思想

**多模式匹配问题**：给定主串 $S$ 和 $k$ 个模式串 $T_1, T_2, \ldots, T_k$，求每个模式串在 $S$ 中的出现位置 / 次数（或所有 $k$ 个模式总共匹配多少次）。

**朴素做法**：对每个 $T_j$ 单独跑 [[KMP]]，$O(k(n + m_j))$——当 $k$ 很大或模式串很多时太慢。

**AC 自动机**（Aho-Corasick）的核心想法——

> 把所有模式串建成一棵 [[Trie]]，再为每个节点构造 **fail 指针**（类似 [[KMP]] 的 $\mathtt{nxt}$）。在 Trie 上扫主串时，沿 fail 链就能 $O(1)$ 知道"当前后缀匹配了哪些模式串"。

**fail 指针的语义**：

> 节点 $u$ 对应字符串 $w_u$（从根到 $u$ 的字符序列）。$\mathtt{fail}[u]$ 指向 $u'$，使得 $w_{u'}$ 是 $w_u$ 的**最长真后缀**且 $w_{u'}$ 是某模式串的**前缀**（即 $u'$ 是 Trie 中的一个节点）。

类比 [[KMP]] 的 $\mathtt{nxt}$——KMP 在线性串上找"最长 border"，AC 自动机在 Trie 上找"最长后缀对应 Trie 节点"。

**用 BFS 逐层构造 fail**：

按 Trie 的深度（BFS 层序）依次处理节点。对节点 $u$ 的某个孩子 $v$（沿字符 $c$ 边）——

> $\mathtt{fail}[v]$ 应该指向 $\mathtt{fail}[u]$ 沿字符 $c$ 走的那个节点。若 $\mathtt{fail}[u]$ 没有 $c$ 出边——递归往上跳 fail，直到根。

实际实现中用**路径压缩**：让 $\mathtt{son}[u][c]$ 直接指向"从 $u$ 出发遇到字符 $c$ 应该到的节点"——若原本没有 $c$ 出边，用 $\mathtt{son}[\mathtt{fail}[u]][c]$ 替代。这样匹配时不再需要循环跳 fail，$O(1)$ 转移。

## 适用场景

- **多模式字符串匹配**（最经典应用）

- **关键词过滤 / 敏感词检测**（业界常用）

- **统计模式串在文本中的出现次数**

- **AC 自动机 + dp**：在自动机节点上做状态转移的字符串 dp

- **某些复杂的字符串问题**：转化为"在自动机上走"的搜索

- 不适用：单模式匹配（[[KMP]] 更简洁）；模式串带通配符（要更复杂的算法）；模式串极长但只一个（[[字符串哈希]] 或后缀数组更优）

## 步骤拆解

1. **建 Trie**：把所有模式串依次插入 Trie。每个串结尾节点打标记（如计数器或编号）

2. **BFS 构造 fail**：

   a. 根的所有直接孩子的 fail 指向根

   b. 把它们加入队列

   c. 队列非空时取出 $u$，对 $u$ 的每个字符 $c$：

     - 若 $u$ 有 $c$ 边（孩子 $v$）：$\mathtt{fail}[v] = \mathtt{son}[\mathtt{fail}[u]][c]$；$v$ 入队

     - 若 $u$ 没有 $c$ 边：把 $\mathtt{son}[u][c]$ 设为 $\mathtt{son}[\mathtt{fail}[u]][c]$（**路径压缩**）

3. **匹配**：从根开始扫主串 $S$——

   a. 对每个字符 $c$，沿 $\mathtt{son}[u][c]$ 转移到下一个节点

   b. 沿 fail 链统计当前位置匹配的所有模式串

## 代码模板

**模板一：AC 自动机（求"主串中匹配多少个不同模式串"）**

```cpp

class ac_automaton {

private:

    static constexpr int ALPHA = 26;

    struct node {

        int son[ALPHA];                         // 转移

        int fail;                               // fail 指针

        int cnt;                                // 以该节点结尾的模式串数（-1 = 已访问）

    };

    vector<node> tr;

    int new_node() {

        node nd;

        for (int i = 0; i < ALPHA; i++) nd.son[i] = 0;

        nd.fail = 0;

        nd.cnt = 0;

        tr.push_back(nd);

        return (int)tr.size() - 1;

    }

public:

    ac_automaton() {

        tr.reserve(1);

        new_node();                             // 0 号是根

    }

    // 插入模式串
    void insert(const string& s) {

        int u = 0;

        for (char c : s) {

            int idx = c - 'a';

            if (!tr[u].son[idx]) {

                tr[u].son[idx] = new_node();

            }

            u = tr[u].son[idx];

        }

        tr[u].cnt += 1;

    }

    // BFS 构造 fail（含路径压缩）
    void build() {

        queue<int> q;

        for (int i = 0; i < ALPHA; i++) {

            if (tr[0].son[i]) {

                tr[tr[0].son[i]].fail = 0;

                q.push(tr[0].son[i]);

            }

        }

        while (!q.empty()) {

            int u = q.front();

            q.pop();

            for (int i = 0; i < ALPHA; i++) {

                int v = tr[u].son[i];

                if (v) {

                    tr[v].fail = tr[tr[u].fail].son[i];

                    q.push(v);

                } else {

                    tr[u].son[i] = tr[tr[u].fail].son[i];   // 路径压缩

                }

            }

        }

    }

    // 求主串 s 中匹配的不同模式串总数
    int query(const string& s) {

        int u = 0;

        int ans = 0;

        for (char c : s) {

            u = tr[u].son[c - 'a'];

            // 沿 fail 链统计

            for (int j = u; j != 0 && tr[j].cnt != -1; j = tr[j].fail) {

                ans += tr[j].cnt;

                tr[j].cnt = -1;                 // 标记已访问，避免重复计数

            }

        }

        return ans;

    }

};
```

> 💡 **`son[u][c] = son[fail[u]][c]` 的精妙**：BFS 处理到 $u$ 时，$\mathtt{fail}[u]$ 已构造好——其 `son[fail[u]][c]` 也已由"路径压缩"递归填好。所以一行代码完成"$u$ 沿 $c$ 失配后跳到何处"的预计算。

> 💡 **`tr[j].cnt = -1` 标记访问过**：避免在沿 fail 链统计时重复计数同一节点。但仅适用于"求多少不同模式串匹配"——若要"计每次匹配次数"，不能这么做。

> ⚠️ **`build()` 必须在所有 `insert()` 之后调用**：路径压缩会修改 son 字段——一旦 build 之后再插入新模式串就会破坏 Trie 结构。

> ⚠️ **`son` 字段的双重含义**：`build` 之前是"真实的 Trie 边"；`build` 之后变成"压缩后的转移函数"——这种"原地修改"是常见但易错的设计。

**模板二：求每个模式串在主串中的出现次数**

某些题目要求"每个 $T_j$ 在 $S$ 中出现多少次"——需要给每个**结尾节点**记下"该节点对应哪个模式串"，然后匹配时不再 `cnt = -1`，而是累加 `cnt` 到对应模式串。

```cpp

// 修改：insert 改为记录"以此节点结尾的模式串编号列表"
// 匹配过程同样沿 fail 链累加；最后用 fail 树自底向上累计

void insert_indexed(const string& s, int id) {

    int u = 0;

    for (char c : s) {

        int idx = c - 'a';

        if (!tr[u].son[idx]) tr[u].son[idx] = new_node();

        u = tr[u].son[idx];

    }

    tr[u].end_id = id;                          // 记录此节点对应模式串 id

}

// 匹配时累加每个节点的"被路过次数"，然后沿 fail 树（拓扑序）累加

```

详见[洛谷P3796](https://www.luogu.com.cn/problem/P3796)/[洛谷P5357](https://www.luogu.com.cn/problem/P5357)的题解，这里不展开。

## 复杂度分析

- 建 Trie：$O\!\left(\sum |T_j|\right)$

- 构造 fail：$O\!\left(\sum |T_j| \cdot |\Sigma|\right)$（$|\Sigma|$ 为字符集大小）

- 匹配：$O(|S| \cdot |\Sigma|)$ 含路径压缩；不含压缩则匹配主体 $O(|S|)$ 但 fail 链遍历可能 $O(|S| + \text{命中数})$

- 总：$O\!\left((\sum |T_j| + |S|) \cdot |\Sigma|\right)$

> 实战中 $|\Sigma| = 26$ 是常数，所以可视作 $O(\sum |T_j| + |S|)$。

## 正确性证明

### fail 指针的定义与构造正确性

**定义重述**：节点 $u$ 对应路径字符串 $w_u$。$\mathtt{fail}[u]$ 是使 $w_{\mathtt{fail}[u]}$ 是 $w_u$ **真后缀**中最长的"在 Trie 中存在的"后缀。

**BFS 构造的正确性**：对节点 $v$（其父亲是 $u$，从 $u$ 沿字符 $c$ 到 $v$），$w_v = w_u + c$。

考察 $w_v$ 的真后缀——

- 它们都形如 $w'_u + c$，其中 $w'_u$ 是 $w_u$ 的真后缀（含空串）

- 我们要找"最长的、且在 Trie 中存在的" $w'_u + c$

**$w_u$ 的真后缀按长度从大到小**：$\mathtt{fail}[u]$ 对应的 $w$、再 $\mathtt{fail}[\mathtt{fail}[u]]$ 对应的 $w$、......、空串。

**判定"$w'_u + c$ 在 Trie 中"**：等价于"$w'_u$ 节点有 $c$ 边"。

**贪心找最长**：从 $\mathtt{fail}[u]$ 开始尝试——若它有 $c$ 边，$\mathtt{fail}[v]$ 就是这个 $c$ 边的目标节点；否则跳到 $\mathtt{fail}[\mathtt{fail}[u]]$ 重试，直到找到或到根。

**路径压缩的等价性**：若节点 $w$ 没有 $c$ 边，路径压缩让 $\mathtt{son}[w][c] = \mathtt{son}[\mathtt{fail}[w]][c]$——递归地，最终指向"$w$ 沿 fail 链上第一个有 $c$ 边的祖先的 $c$ 出边"。这等价于"$w$ 反复跳 fail 直到找到 $c$ 边"。

所以一行 `tr[v].fail = tr[tr[u].fail].son[i]` 正是"$w_u$ 反复跳 fail 找 $c$ 边"的简洁实现。$\blacksquare$

### BFS 顺序的必要性

**为什么必须 BFS（按 Trie 深度）**：构造 $\mathtt{fail}[v]$ 时用到 $\mathtt{fail}[u]$ 和 $\mathtt{son}[\mathtt{fail}[u]][c]$——其中 $\mathtt{fail}[u]$ 的深度严格小于 $u$，$\mathtt{son}[\mathtt{fail}[u]][c]$ 深度也 $<$ $v$ 的深度（要么浅要么相等但必早处理）。

按 BFS 顺序处理保证"父节点 + fail 关联节点都已处理完"——递推合法。$\blacksquare$

### 匹配过程的正确性

**关键不变量**：扫主串到位置 $i$、当前节点 $u$ 时——$w_u$ 是 $S[1..i]$ 的最长后缀，且 $w_u$ 是某模式串的前缀（在 Trie 中存在）。

**证明（归纳）**：

**初始** $i = 0, u = 0$：$w_0 = $ 空串，是 $S$ 的空后缀，平凡成立。

**归纳**：假设 $S[1..i]$ 的最长 Trie 后缀对应节点 $u$。处理 $S[i+1] = c$——

- 若 $u$ 有真实 $c$ 边到 $v$：$w_v = w_u + c$ 是 $S[1..i+1]$ 的后缀且在 Trie 中——是最长的吗？

  **是**：若有更长的 Trie 后缀 $w'$，则 $w'$ 去掉最后一个字符后是 $S[1..i]$ 的更长 Trie 后缀，与 $w_u$ 是最长矛盾。

- 若 $u$ 没有真实 $c$ 边：路径压缩后 $\mathtt{son}[u][c]$ 指向"$u$ 沿 fail 链跳到的某节点 $w$ 的 $c$ 边目标"——$w_w$ 是 $w_u$ 的最长后缀使得 $w_w + c$ 在 Trie 中。所以转移正确。$\blacksquare$

### 沿 fail 链统计匹配的合法性

**命题**：$S[1..i]$ 的所有"在 Trie 中存在的后缀"恰好是节点 $u$（当前位置）以及 $u$ 沿 fail 链上经过的所有节点。

**证明**：由 fail 定义——$\mathtt{fail}[u]$ 是 $w_u$ 的最长真后缀且在 Trie 中。所以从 $u$ 沿 fail 不断跳，对应 $w_u$ 的所有"在 Trie 中存在的"后缀（按长度从大到小）。

**应用**：每个**模式串**对应 Trie 中某个节点（结尾节点）。某模式串 $T_j$ 在 $S$ 中位置 $i$ 处结束 $\Leftrightarrow$ $T_j$ 是 $S[1..i]$ 的一个后缀 $\Leftrightarrow$ $T_j$ 对应节点在"$u$ 的 fail 链"上。

所以扫主串时，每到一个 $u$ 就沿 fail 链遍历——能找出**所有** "在此位置结束的模式串"。$\blacksquare$

### 复杂度的来源

- **建 Trie**：$O(\sum |T_j|)$，每个字符插入 $O(1)$

- **构造 fail**：BFS 共 $O(总节点数 \cdot |\Sigma|) = O((\sum |T_j|) \cdot |\Sigma|)$

- **匹配**（无 fail 链统计）：路径压缩后每字符 $O(1)$ 转移，总 $O(|S|)$

- **匹配 + fail 链统计**：每节点 fail 链长度 $O(\text{深度})$，但用 `cnt = -1` 标记访问过的节点，每节点至多被沿 fail 链访问一次——总 $O(|S| + \text{命中节点数})$

$\blacksquare$

## 关于 fail 树

**fail 树**：把所有节点视为节点，每个非根节点 $u$ 与 $\mathtt{fail}[u]$ 之间连边——形成一棵以根为根的**树**。

**性质**：节点 $v$ 是节点 $u$ 在 fail 树上的祖先 $\Leftrightarrow$ $w_v$ 是 $w_u$ 的后缀。

**应用**：

- **求"模式串 $T_j$ 在 $S$ 中出现次数"**：先扫主串记下每个节点"被到达次数"，再在 fail 树上做后缀和——节点 $u$ 的子树和就是 $w_u$ 在 $S$ 中作为后缀出现的总次数。

- **AC 自动机 + dp**：在自动机节点上做状态转移；fail 树常作为转移辅助。

## 与相关算法的对比

| 算法               | 适用               | 复杂度                    | 备注                   |
| ---------------- | ---------------- | ---------------------- | -------------------- |
| [[KMP]]          | 单模式              | $O(n + m)$             | 简单 $\mathtt{nxt}$ 数组 |
| AC 自动机           | 多模式              | $O(\sum m_i + n)$      | KMP 在 Trie 上的推广      |
| [[字符串哈希]]        | 单模式（小概率误判）       | $O(n + m)$             | 实现简短                 |
| 后缀数组 / 后缀自动机     | 单字符串的复杂查询        | $O(n \log n)$ / $O(n)$ | 处理"子串"问题             |

**经验**：见到"多模式匹配""敏感词过滤"——AC 自动机是标准答案。其他场景慎用（代码长，单模式杀鸡用牛刀）。

## 几个常见错误

- **`build()` 后再 `insert()`**：路径压缩破坏 Trie 结构——必须先全部插入再 build

- **`son` 字段的双重含义**：build 前是 Trie 边（可能 0），build 后是转移函数（必有值）。处理时要清楚自己在哪一步

- **fail 链统计死循环**：`for (j; j; j = fail[j])` 必须保证 `fail[根] = 0`（根的 fail 是它自己或 0），否则可能死循环

- **多个相同模式串**：`tr[u].cnt += 1` 而非 `= 1`——多次插入同一串应累加

- **字符集大小**：默认 26 字母；含数字、特殊字符要扩大 ALPHA

## 相关例题

- [洛谷P3808 【模板】AC 自动机（简单版）](https://www.luogu.com.cn/problem/P3808)

- [洛谷P3796 【模板】AC 自动机（加强版）](https://www.luogu.com.cn/problem/P3796)

- [洛谷P5357 【模板】AC 自动机（二次加强版）](https://www.luogu.com.cn/problem/P5357)

$\blacksquare$