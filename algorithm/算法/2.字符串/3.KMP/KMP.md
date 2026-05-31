#难度/★★★★

> 用预处理的"失配数组" $\mathtt{nxt}$ 让模式串失配时不必从头重启——$O(n + m)$ 完成"主串中找模式串所有位置"的经典字符串匹配。

## 前置知识

- [[字符串模拟]]

## 核心思想

**问题**：给定主串 $S$（长度 $m$）和模式串 $T$（长度 $n$），找出 $T$ 在 $S$ 中所有出现的位置。

**朴素做法**：枚举 $S$ 的每个起点 $i$，把 $T$ 与 $S[i..]$ 逐字符比较——失配则 $i$ 推进 1。最坏 $O(nm)$。

**KMP 算法**（Knuth-Morris-Pratt）的核心洞察：

> 失配时，主串指针 $i$ **不回退**——只让模式串指针 $j$ 跳到一个"已知合法的部分匹配"位置。这个位置由模式串自身的结构决定。

**关键概念——border**：

> 字符串 $T[1..k]$ 的 **border** 是既是 $T[1..k]$ 的**真前缀**又是它的**真后缀**的字符串（不含 $T[1..k]$ 自身）。

例如 $T = \mathtt{abcabc}$ 的最长 border 是 $\mathtt{abc}$（长度 3）；$T = \mathtt{abab}$ 的最长 border 是 $\mathtt{ab}$（长度 2）。

**$\mathtt{nxt}$ 数组（失配数组）**：

> $\mathtt{nxt}[i] = T[1..i]$ 的**最长 border 的长度**。

例如 $T = \mathtt{abcabd}$：

| $i$               | 1   | 2   | 3   | 4   | 5   | 6   |
| ----------------- | --- | --- | --- | --- | --- | --- |
| $T[i]$            | a   | b   | c   | a   | b   | d   |
| $\mathtt{nxt}[i]$ | 0   | 0   | 0   | 1   | 2   | 0   |

**$\mathtt{nxt}$ 的用法**——匹配过程中，若当前已匹配 $T[1..j]$ 但下一个字符 $T[j+1]$ 与主串不符（失配）：

> 让 $j$ 跳到 $\mathtt{nxt}[j]$——意为"舍弃当前 $T[1..j]$ 的尾部，保留它的最长 border 部分"，因为这部分作为新的"已匹配前缀"是合法的。

这样 $j$ 跳得越来越短，但**主串指针 $i$ 不动**——避免了朴素算法的"$i$ 回退"。

## 适用场景

- **字符串单模式匹配**：找 $T$ 在 $S$ 中所有出现位置（最经典应用）

- **求字符串的所有 border**：$\mathtt{nxt}[n], \mathtt{nxt}[\mathtt{nxt}[n]], \ldots$ 序列——一次跳到底就是所有 border 长度

- **求字符串的最短循环节**：若 $n - \mathtt{nxt}[n]$ 整除 $n$，则它是最短循环节长度

- **某些回文 / 周期问题**：通过构造特殊串 + KMP 解决

- 不适用：多模式匹配（用 [[AC自动机]]）；带通配符的匹配（用更复杂的算法）；只需大致判断的场景（用 [[字符串哈希]]）

## 步骤拆解

**构造 $\mathtt{nxt}$**（双指针 + 自匹配）：

> 把 $T$ 和它自己做匹配——$T$ 既是"主串"又是"模式串"。

1. $\mathtt{nxt}[1] = 0$

2. 双指针 $i$（当前位置，从 2 到 $n$）和 $j$（已匹配 border 长度）

3. 处理 $T[i]$：

   - 若 $T[i] \ne T[j+1]$：$j \leftarrow \mathtt{nxt}[j]$，重试（直到 $j = 0$ 或匹配上）

   - 若 $T[i] = T[j+1]$：$j$ 加 1

1. $\mathtt{nxt}[i] = j$

**用 $\mathtt{nxt}$ 做匹配**：

1. 双指针 $i$（主串位置，从 1 到 $m$）和 $j$（模式串已匹配长度）

2. 处理 $S[i]$：

   - 若 $S[i] \ne T[j+1]$：$j \leftarrow \mathtt{nxt}[j]$（直到 $j = 0$ 或匹配上）

   - 若 $S[i] = T[j+1]$：$j$ 加 1

3. 若 $j = n$：找到一次匹配，起始位置为 $i - n + 1$；继续找用 $j \leftarrow \mathtt{nxt}[j]$

## 代码模板

> **下标约定**：本笔记用 1-indexed 数组——$\mathtt{nxt}[i]$ 对应 $T$ 的前 $i$ 个字符。但 C++ 的 `string` 本身是 0-indexed，所以代码中 `t[i - 1]` 表示"第 $i$ 个字符"。

**模板：完整 KMP（构造 + 匹配）**

```cpp
class kmp {

private:

    int n;

    string t;

    vector<int> nxt;                            // nxt[i] = t 前 i 个字符的最长 border 长度

public:

    kmp(const string& pattern) {

        t = pattern;

        n = t.size();

        nxt.assign(n + 1, 0);

        // nxt[1] = 0（单字符无真前缀）

        for (int i = 2, j = 0; i <= n; i++) {

            while (j > 0 && t[i - 1] != t[j]) {

                j = nxt[j];                     // 失配回跳

            }

            if (t[i - 1] == t[j]) {

                j++;

            }

            nxt[i] = j;

        }

    }

    // 在主串 s 中找所有 t 的出现位置（返回起始位置，1-indexed）
    vector<int> match(const string& s) {

        vector<int> positions;

        int m = s.size();

        for (int i = 1, j = 0; i <= m; i++) {

            while (j > 0 && s[i - 1] != t[j]) {

                j = nxt[j];

            }

            if (s[i - 1] == t[j]) {

                j++;

            }

            if (j == n) {

                positions.push_back(i - n + 1);

                j = nxt[j];                     // 继续找下一次出现

            }

        }

        return positions;

    }

    int border_len(int i) {

        return nxt[i];                          // 暴露 nxt 给外部用

    }

};
```

> 💡 **`t[i - 1]` 与 `t[j]` 的对应关系**：1-indexed 视角下当前要处理 $T$ 的第 $i$ 个字符即 `t[i - 1]`；要比较的是"已匹配 border 长度 $j$ 的下一个字符"即 $T$ 第 $j + 1$ 个字符即 `t[j]`。这是混合下标的常见易错点。

> 💡 **`while + if` 的简洁结构**：失配时 `j = nxt[j]` 反复回跳；最终要么匹配上（`if` 加 1）、要么 $j$ 归零（外层 while 终止）。两种情形通过 if 的"是否进入"统一处理。

> ⚠️ **找全部出现 vs 只找首次**：找到一次后 `j = nxt[j]` 让 KMP 继续——能找出**全部重叠**的出现（如在 $\mathtt{aaaa}$ 中找 $\mathtt{aa}$ 会得到 3 次）。若只想找一次，找到后直接 break。

## 复杂度分析

- 预处理 $\mathtt{nxt}$：$O(n)$（均摊分析）

- 匹配阶段：$O(m)$（均摊）

- 总时间：$O(n + m)$

- 空间：$O(n)$

## 正确性证明

### $\mathtt{nxt}$ 数组的递推正确性

**定义**：$\mathtt{nxt}[i]$ 是 $T[1..i]$ 的最长 border 长度。

**关键观察——border 的递归结构**：

若 $T[1..i]$ 的最长 border 长度是 $k$（$k \ge 1$），则 $T[1..k]$ 也必是 $T[1..i]$ 的某个 border。

进一步——$T[1..i-1]$ 的所有 border 集合可以通过反复跳 $\mathtt{nxt}$ 取得（因为最长 border 的 border 也是 border）。

**$\mathtt{nxt}[i]$ 的递推**：

要求 $T[1..i]$ 的最长 border。基于 $\mathtt{nxt}[i-1]$ 推 $\mathtt{nxt}[i]$——

- 设 $j = \mathtt{nxt}[i - 1]$，即 $T[1..j]$ 是 $T[1..i-1]$ 的最长 border

- 若 $T[j + 1] = T[i]$：$T[1..j+1]$ 是 $T[1..i]$ 的 border（长度 $j + 1$）

- 否则：尝试**更短的 border**——$T[1..i-1]$ 的次长 border 长度是 $\mathtt{nxt}[\mathtt{nxt}[i-1]] = \mathtt{nxt}[j]$。回跳后再判

- 若一直跳到 $j = 0$ 仍不行：$\mathtt{nxt}[i] = 0$（除非 $T[1] = T[i]$，否则）

**正确性的关键引理**：

> 若 $T[1..k]$ 是 $T[1..i-1]$ 的某 border 且 $T[k + 1] = T[i]$，则 $T[1..k + 1]$ 是 $T[1..i]$ 的 border。

证明显然——$T[1..k+1]$ 既是 $T[1..i]$ 前缀（取前 $k+1$ 字符），又是后缀（前 $k$ 字符是 $T[1..i-1]$ 的后缀，加上 $T[i] = T[k+1]$）。

**完备性（最长 border 必被找到）**：

设 $T[1..k]$ 是 $T[1..i]$ 的最长 border（$k \ge 1$）。则 $T[1..k-1]$ 是 $T[1..i-1]$ 的某 border（去掉两端最后一个字符）——它要么是最长 border（$k - 1 = \mathtt{nxt}[i-1]$），要么是更短的。

算法从 $j = \mathtt{nxt}[i-1]$ 开始跳，遍历 $T[1..i-1]$ 的所有 border 长度——必能在某轮跳到 $j = k - 1$，那时 $T[k] = T[i]$ 满足，得到长度 $k$ 的 border。$\blacksquare$

### 匹配过程的正确性

**关键不变量**：在匹配主循环的任意时刻，若已处理到主串第 $i$ 字符且 $j$ 是当前模式串"已匹配长度"，则——

> $T[1..j]$ 是 $S[i - j + 1 .. i]$ 的**精确前缀**（即两者完全相等）。

**证明（归纳）**：

**初始**：$i = 0, j = 0$ 时不变量平凡成立。

**归纳**：假设处理到 $i, j$ 时不变量成立。处理 $S[i + 1]$——

- **情况 1**：$S[i + 1] = T[j + 1]$。模式串前 $j + 1$ 字符与 $S$ 相应部分匹配——更新 $j \leftarrow j + 1$ 后不变量保持。

- **情况 2**：$S[i + 1] \ne T[j + 1]$。失配。**必须**改变 $j$ 才能保持不变量——

  失配后 $j$ 跳到 $\mathtt{nxt}[j]$——为什么这是对的？$T[1..\mathtt{nxt}[j]]$ 是 $T[1..j]$ 的 border，所以也是 $S[i - j + 1 .. i]$ 的后缀（既是 $T[1..j]$ 后缀，而 $T[1..j] = S[\ldots]$）——即 $T[1..\mathtt{nxt}[j]] = S[i - \mathtt{nxt}[j] + 1 .. i]$。

  跳后 $j' = \mathtt{nxt}[j]$，主串指针仍是 $i$（未推进）——不变量 $T[1..j'] = S[i - j' + 1 .. i]$ 正确成立。

由不变量，**当 $j = n$ 时** $T = S[i - n + 1 .. i]$——即 $T$ 在 $S$ 中位置 $i - n + 1$ 处出现。$\blacksquare$

### 复杂度的均摊分析

**关键观察**：算法中 $j$ 的变化只有两种——

- **加 1**：每次主循环至多一次（`if` 中）

- **减少**：通过 `j = nxt[j]` 跳跃

**加 1 总次数 $\le m$**（主循环跑 $m$ 次，每次至多加 1）。所以 $j$ 整个过程"加了" $\le m$ 次。

**减少不超过加 1 次数**：$j \ge 0$ 始终成立——所以"减少总量" $\le$ "加 1 总量" $\le m$。

**总时间** = 加 1 次数 + 减少次数 $\le 2m$。匹配阶段 $O(m)$。

**预处理 $\mathtt{nxt}$ 同理**：$O(n)$。

**总 $O(n + m)$**。$\blacksquare$

## 应用：求最短循环节

**问题**：给字符串 $T$，求最短循环节长度（若 $T$ 是 $T_0$ 重复 $k$ 次而成，求最短的这种 $T_0$ 的长度）。

**答案**：若 $n - \mathtt{nxt}[n]$ 整除 $n$，则它就是最短循环节长度；否则 $T$ 没有"完整重复"的循环节，整串就是它自己的循环节。

**证明（直觉）**：$T$ 最长 border 的长度 $\mathtt{nxt}[n]$ 表示"$T$ 的前缀与后缀有 $\mathtt{nxt}[n]$ 字符重合"——意味着 $T$ 的"周期"是 $n - \mathtt{nxt}[n]$（每移 $n - \mathtt{nxt}[n]$ 字符还能对齐自己）。若这个周期整除 $n$，则它就是循环节长度；否则只是"近似周期"，没有完整循环。

```cpp

int min_period(const string& t) {

    kmp k(t);

    int n = t.size();

    int border = k.border_len(n);

    int period = n - border;

    if (n % period == 0) return period;

    return n;                                   // 整串就是循环节

}

```

## 应用：所有 border

**问题**：求字符串 $T$ 的所有 border 长度。

**答案**：从 $n$ 开始反复跳 $\mathtt{nxt}$ 即可。

```cpp

vector<int> all_borders(const string& t) {

    kmp k(t);

    int n = t.size();

    vector<int> borders;

    int j = k.border_len(n);

    while (j > 0) {

        borders.push_back(j);

        j = k.border_len(j);

    }

    return borders;

}

```

## 与相关算法的对比

| 算法               | 复杂度        | 适用               | 思想                       |
| ---------------- | ---------- | ---------------- | ------------------------ |
| KMP              | $O(n + m)$ | 单模式匹配            | 失配数组，$j$ 不回退             |
| [[字符串哈希]]        | $O(n + m)$ | 单模式匹配（小概率误判）     | 滑动窗口哈希                   |
| Z 算法             | $O(n + m)$ | 单模式匹配            | Z 数组（每位置最长前缀匹配）          |
| [[AC自动机]]        | $O(n + m)$ | 多模式匹配（同时找 $k$ 个） | KMP 在 [[Trie]] 上的推广      |

**经验**：单模式严格无误差选 KMP；要求快速实现且能容忍极小误判用哈希；多模式必须 [[AC自动机]]。

## 几个常见错误

- **`nxt[1]` 误设非零**：单字符无真前缀，必须 0

- **`while + if` 顺序错**：失配时**先**跳到底再判加 1，顺序反了会出错

- **找全部出现忘记 `j = nxt[j]`**：不加这行只能找首次出现

- **下标边界**：1-indexed 与 0-indexed 混用最容易出错。坚持用一种风格

- **`t[i - 1]` vs `t[j]`**：当前位置 vs 比较位置——容易混

## 相关例题

  

- [洛谷P3375 【模板】KMP 字符串匹配](https://www.luogu.com.cn/problem/P3375)

- [洛谷P4391 [BOI2009] Radio Transmission 无线传输](https://www.luogu.com.cn/problem/P4391)

- [洛谷P3435 [POI2006] OKR-Periods of Words](https://www.luogu.com.cn/problem/P3435)

$\blacksquare$