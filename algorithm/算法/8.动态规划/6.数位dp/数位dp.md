#难度/★★★★

> "在 $[a, b]$ 中有多少个数满足某种数位性质？"—— 按位从高到低 dp，配合 $\mathtt{limit}$ / $\mathtt{lead}$ 两个标志位与题目相关的累积状态 $\mathtt{state}$，几乎是模板化的。

## 前置知识

- [[记忆化搜索]]

- [[线性dp]]

## 核心思想

数位 dp 解决的是这样一类问题——

> **求 $[a, b]$ 范围内满足某种"数位约束"的整数个数**：相邻数字差 $\ge 2$、不含连续 4 个 6、数字之和为定值、含特定子串……

朴素枚举每个数 $O(b - a)$ 在 $b \sim 10^{18}$ 时不可能；但**只有 $O(\log b)$ 位**——按位 dp 复杂度只与位数和状态数相关，与 $b$ 的大小无关。

**第一步：把区间转化为前缀**

$$|\{n \in [a, b] : P(n)\}| = |\{n \in [0, b] : P(n)\}| - |\{n \in [0, a-1] : P(n)\}|$$

定义 $\mathtt{count\_le}(N)$ 为 $[0, N]$ 中满足性质 $P$ 的数的个数，原问题 = $\mathtt{count\_le}(b) - \mathtt{count\_le}(a - 1)$。

**第二步：按位 dp**

把 $N$ 写成 $d_0 d_1 \cdots d_{L-1}$（$d_0$ 最高位、$L$ 位数）。**从高位到低位**依次决定每一位填什么——但必须保证最终填出的数 $n \le N$。

朴素地说，每一位有两种状态：

- "**贴 $N$ 的上界**" —— 前面所有位都恰好等于 $N$ 对应位，则当前位最多填 $d_{\mathtt{pos}}$

- "**未贴上界**" —— 之前某位已严格 $< N$ 对应位，则当前位可填 $0 \sim 9$ 任意

这个二分用一个标志位 $\mathtt{limit}$ 表达。**关键观察**：当 $\mathtt{limit} = \mathtt{false}$ 时，无论 $N$ 具体是多少，"剩下还能填多少种合法数" 只依赖当前位置与已累积的状态——这就允许**记忆化**！

**第三步：处理前导零**

若题目要求"$n$ 是从某种最高位开始的合法数串"（如相邻数字差），前导零阶段的"上一位"不应参与约束判断（前导零不是真实的数字位）。用 $\mathtt{lead}$ 标志区分——

- $\mathtt{lead} = \mathtt{true}$：当前仍是前导零阶段，填 0 继续前导零、填 $\ge 1$ 的数字开始真正的数位

- $\mathtt{lead} = \mathtt{false}$：已开始真正的数位，必须遵守题目所有约束

> 💡 **三大要素**：$\mathtt{limit}$（贴 $N$ 上界）、$\mathtt{lead}$（前导零）、$\mathtt{state}$（题目相关的累积状态，如"上一位"、"已用数字之和"……）。任何数位 dp 题都可套这个框架。

> ⚠️ **记忆化只在 `!limit && !lead` 时合法**：
>
> - $\mathtt{limit} = \mathtt{true}$ 时，可填的最大数字依赖 $N$ 的具体上界，不同 $N$ 的答案不同——不能复用
>
> - $\mathtt{lead} = \mathtt{true}$ 时，"前导零下的累积状态"和"真正数位下的累积状态"语义不同，混存会出错

## 经典例题：windy 数

> **windy 数**定义为相邻两位数字之差**绝对值 $\ge 2$** 的非负整数（如 135、24680 是；123、66 不是）。求 $[a, b]$ 内 windy 数的个数。

**状态怎么想**：约束是"相邻两位差 $\ge 2$"——决定第 $\mathtt{pos}$ 位时需要知道**上一位填了什么**。所以 $\mathtt{state}$ 设为"上一位的数字" $\mathtt{last}$。

加上 $\mathtt{limit}$ 和 $\mathtt{lead}$，dp 函数 $\mathtt{dfs}(\mathtt{pos}, \mathtt{last}, \mathtt{limit}, \mathtt{lead})$ 返回——"从第 $\mathtt{pos}$ 位开始，上一位为 $\mathtt{last}$，前缀是否贴上界、是否仍前导零，能填出多少个合法 windy 数"。

**转移**：枚举当前位填 $d \in [0, \mathtt{max\_d}]$（$\mathtt{max\_d}$ 取决于 $\mathtt{limit}$）——

$$\mathtt{dfs}(\mathtt{pos}, \mathtt{last}, \mathtt{limit}, \mathtt{lead}) = \sum_{d=0}^{\mathtt{max\_d}} [\text{填 } d \text{ 合法}] \cdot \mathtt{dfs}(\mathtt{pos+1}, \mathtt{new\_last}, \mathtt{new\_limit}, \mathtt{new\_lead})$$

其中——

- "**填 $d$ 合法**"：若 $\mathtt{lead} = \mathtt{true}$ 总是合法（前导零阶段没有上一位的约束）；若 $\mathtt{lead} = \mathtt{false}$ 则需 $|d - \mathtt{last}| \ge 2$

- $\mathtt{new\_last} = d$（若已离开前导零），否则保持 $\mathtt{last}$ 不变

- $\mathtt{new\_limit} = \mathtt{limit} \wedge (d = \mathtt{max\_d})$（贴上界传递）

- $\mathtt{new\_lead} = \mathtt{lead} \wedge (d = 0)$（前导零传递）

**边界**：$\mathtt{pos} = L$（填满所有位）时返回 1（一种合法方案）。

> 💡 **`last` 的"前导零占位符"**：实现中用 $\mathtt{last} = 10$（一个不可能的真实数字）表示"前导零阶段没有上一位"——这样所有状态对都用整数表示，便于记忆化数组下标。

## 适用场景

- 区间 $[a, b]$ 内满足某种"数位约束"的数的计数

- 经典约束：相邻差、含/不含某子串、数字之和、各位平方和、含特定数字次数

- 数位上的累加问题（如 $\sum_{i=a}^{b} f(\text{数位}(i))$）

- 不适用：约束不是"按位"的（如约束 $n$ 是质数）；$N$ 极大但约束跨越多位窗口（要更复杂的状态）

## 步骤拆解

1. **判断是不是数位 dp**：约束按位、$N$ 大、$a$ 到 $b$ 范围广

2. **把 $N$ 拆位**：$d_0 d_1 \cdots d_{L-1}$，$L = O(\log N)$

3. **设状态**：$\mathtt{state}$ 为题目相关的累积量（最近一位、和、是否含某串……）

4. **写 $\mathtt{dfs}(\mathtt{pos}, \mathtt{state}, \mathtt{limit}, \mathtt{lead})$**：枚举 $d \in [0, \mathtt{max\_d}]$，递归求和

5. **记忆化**：用 $\mathtt{memo}[\mathtt{pos}][\mathtt{state}]$ 缓存，但只在 $!\mathtt{limit} \wedge !\mathtt{lead}$ 时读 / 写

6. **区间转换**：$\mathtt{count\_le}(b) - \mathtt{count\_le}(a - 1)$

## 代码模板

**模板：windy 数**

```cpp

class windy_count {

private:

    vector<int> digits;                                 // 高位到低位

    int len;

    vector<vector<long long>> memo;                     // memo[pos][last]

    long long dfs(int pos, int last, bool limit, bool lead) {

        if (pos == len) {

            return 1;                                   // 填完所有位，得到一个合法数

        }

        if (!limit && !lead && memo[pos][last] != -1) {

            return memo[pos][last];

        }

        int max_d = limit ? digits[pos] : 9;

        long long ans = 0;

        for (int d = 0; d <= max_d; d++) {

            if (!lead && abs(d - last) < 2) continue;   // windy 约束

            bool new_lead = lead && (d == 0);

            int new_last = new_lead ? last : d;         // 前导零阶段保持占位符

            ans += dfs(pos + 1, new_last,

                       limit && (d == max_d),

                       new_lead);

        }

        if (!limit && !lead) {

            memo[pos][last] = ans;

        }

        return ans;

    }

    long long count_le(long long N) {

        if (N < 0) return 0;

        digits.clear();

        if (N == 0) {

            digits.push_back(0);

        } else {

            long long t = N;

            while (t > 0) {

                digits.push_back(t % 10);

                t /= 10;

            }

            reverse(digits.begin(), digits.end());

        }

        len = digits.size();

        // last ∈ [0, 9] 或 10（前导零占位符）

        memo.assign(len, vector<long long>(11, -1));

        return dfs(0, 10, true, true);                  // 初始：贴上界、前导零、占位 last=10

    }

public:

    long long count_in(long long a, long long b) {

        return count_le(b) - count_le(a - 1);

    }

};
```

> ⚠️ **`memo` 必须每次 `count_le` 调用前重置**：因为 $\mathtt{count\_le}(b)$ 和 $\mathtt{count\_le}(a-1)$ 是两个不同 $N$ 的查询，**但** $!\mathtt{limit} \wedge !\mathtt{lead}$ 的状态值与 $N$ 无关——理论上可以复用！实际写法分两种：
>
> - **每次重置**：保守但易写
>
> - **永久缓存**：只重置一次，效率更高（适用于多次查询）
>
> 本模板采用每次重置，避免初学者的混淆。

> 💡 **关于 0 是否计入**：$\mathtt{count\_le}(N)$ 包含 0——当整个过程都是前导零（$d$ 始终为 0）时，$\mathtt{pos} = L$ 终止处返回 1。这表示"数 0 本身"被算入。若题目要求 $[1, b]$，可用 $\mathtt{count\_le}(b) - \mathtt{count\_le}(0)$ 或在 $\mathtt{count\_le}$ 内特判。

## 复杂度分析

- 时间复杂度：$O(L \cdot S \cdot 10)$

  - $L = O(\log N)$ 位

  - $S$ 是状态数（windy 数为 $11$；数字之和等问题为 $O(L \cdot 9)$）

  - 每个状态枚举 $10$ 个数字

- 空间复杂度：$O(L \cdot S)$（记忆化数组）

> 💡 **典型量级**：$N \le 10^{18}$ 时 $L \approx 19$，状态数通常 $\le 100$，总操作数 $\le 2 \times 10^4$——常数极小，几乎瞬间出结果。

## 正确性证明

### `limit` 标志的传递

**命题**：$\mathtt{dfs}(\mathtt{pos}, \cdot, \mathtt{limit}, \cdot)$ 正确枚举的数恰好满足"前 $\mathtt{pos}$ 位拼接得到的数 $\le$ $N$ 的前 $\mathtt{pos}$ 位"。

**证明**：

- $\mathtt{pos} = 0$ 时初始 $\mathtt{limit} = \mathtt{true}$，"$N$ 的前 0 位"是空，平凡成立

- 归纳：设 $\mathtt{dfs}(\mathtt{pos}, \cdot, \mathtt{limit}, \cdot)$ 正确。考察填入 $d \in [0, \mathtt{max\_d}]$ 后递归 $\mathtt{dfs}(\mathtt{pos} + 1, \cdot, \mathtt{new\_limit}, \cdot)$——

  - **若 $\mathtt{limit} = \mathtt{true}$**：前 $\mathtt{pos}$ 位恰等于 $N$ 的前 $\mathtt{pos}$ 位，$\mathtt{max\_d} = d_{\mathtt{pos}}$。

    - $d < d_{\mathtt{pos}}$：前 $\mathtt{pos}+1$ 位严格 $<$ $N$ 的前 $\mathtt{pos}+1$ 位—— $\mathtt{new\_limit}$ 应为 $\mathtt{false}$，代码中 $\mathtt{limit} \wedge (d = \mathtt{max\_d}) = \mathtt{true} \wedge \mathtt{false} = \mathtt{false}$ ✓

    - $d = d_{\mathtt{pos}}$：前 $\mathtt{pos}+1$ 位恰等—— $\mathtt{new\_limit} = \mathtt{true}$，代码中为 $\mathtt{true} \wedge \mathtt{true} = \mathtt{true}$ ✓

  - **若 $\mathtt{limit} = \mathtt{false}$**：前 $\mathtt{pos}$ 位已严格 $<$ —— 任何后续填法都保持严格 $<$，$\mathtt{new\_limit} = \mathtt{false}$，代码中 $\mathtt{limit} \wedge \cdots = \mathtt{false}$ ✓

由归纳，整个 dfs 枚举的数恰好都 $\le N$。$\blacksquare$

### 记忆化的合法性

**命题**：$\mathtt{memo}[\mathtt{pos}][\mathtt{state}]$ 在 $!\mathtt{limit} \wedge !\mathtt{lead}$ 下记录的值，对所有调用都正确。

**证明**：当 $\mathtt{limit} = \mathtt{false}$ 时，从第 $\mathtt{pos}$ 位起每位都可填 $[0, 9]$，与 $N$ 的具体值无关；当 $\mathtt{lead} = \mathtt{false}$ 时，约束语义稳定（题目约束已生效，与前面是否有过前导零无关）。所以 $\mathtt{dfs}$ 的返回值**仅依赖** $(\mathtt{pos}, \mathtt{state})$——任何两次调用结果相同，记忆化合法。

反之，若 $\mathtt{limit} = \mathtt{true}$，$\mathtt{max\_d}$ 依赖 $N$ 的当前位——不同 $N$ 在同一 $(\mathtt{pos}, \mathtt{state})$ 的返回值不同，不能缓存。$\mathtt{lead} = \mathtt{true}$ 时，$\mathtt{state}$ 中可能含"前导零占位符"，语义与"真正数位下的同一 state 值"完全不同。$\blacksquare$

### 区间转换的正确性

**命题**：$|\{n \in [a, b] : P(n)\}| = \mathtt{count\_le}(b) - \mathtt{count\_le}(a - 1)$。

**证明**：$[a, b] = [0, b] \setminus [0, a-1]$（$a \ge 0$ 时）。两集合在合法数 $P$ 下的差即所求。$\blacksquare$

## 应用扩展

### 应用一：数字之和约束

> 求 $[0, N]$ 中数字各位之和**等于 $S$** 的数的个数。

$\mathtt{state}$ = "已填位的数字之和"。$\mathtt{dfs}(\mathtt{pos}, \mathtt{sum}, \mathtt{limit}, \mathtt{lead})$——

- 当 $\mathtt{pos} = L$ 时，若 $\mathtt{sum} = S$ 返回 1 否则 0

- 枚举 $d$，递归 $\mathtt{dfs}(\mathtt{pos}+1, \mathtt{sum} + d, \cdots)$

这种题通常不需要 $\mathtt{lead}$ 标志（"和"本身不受前导零影响——前导零的"贡献"是 0），但加上更安全。

### 应用二：不含特定子串

> 求 $[0, N]$ 中**不含**子串 "62" 的数。

$\mathtt{state}$ = "上一位是否是 6"。枚举 $d$ 时若 $\mathtt{state} = 1 \wedge d = 2$ 则非法。状态数仅 2，常数极小。

更复杂的多字符模式可用 [[KMP]] 的失配函数把"匹配进度"作为 $\mathtt{state}$——结合数位 dp 可统计含 / 不含任意模式串的数。

### 应用三：1 到 N 中每个数字出现次数

> 统计 $1 \sim N$ 中数字 $0, 1, \ldots, 9$ 各自出现的次数。

固定目标数字 $t$，定义 $\mathtt{dfs}(\mathtt{pos}, \mathtt{cnt}, \mathtt{limit}, \mathtt{lead})$ 返回"贡献的 $t$ 出现总次数"——

- 每次填 $d$，若 $d = t \wedge !\mathtt{lead}$（或 $t \ne 0$）累加 $1$ 进 $\mathtt{cnt}$

- 终态返回 $\mathtt{cnt}$

> ⚠️ **数字 0 的特别处理**：统计 0 出现次数时，前导零**不算**——所以 $t = 0$ 时只能在 $\mathtt{lead} = \mathtt{false}$ 时累加。

也有更高效的"按位组合公式"做法（$O(\log N)$ 无 dp），但数位 dp 写法是通法。

## 几个常见错误

- **记忆化条件错位**：在 $\mathtt{limit} = \mathtt{true}$ 时读 / 写 $\mathtt{memo}$ 是高频 bug，结果会受 $N$ 污染

- **`lead` 处理不当**：把前导零阶段当作普通数位，导致 "$N = 100$ 时被当成 '001'，'001' 触发了不该有的约束"——必须显式区分

- **`new_last` 写错**：前导零阶段填 0 时 $\mathtt{last}$ 应保持占位符；写成 $\mathtt{new\_last} = d$ 会让占位符被 0 覆盖，可能误触发约束

- **$N$ 拆位时漏处理 $N = 0$**：$N = 0$ 时 `while` 循环不执行，$\mathtt{digits}$ 为空——需特判

- **大数边界**：$N \le 10^{18}$ 时 $a - 1$ 可能在 $a = 0$ 时变成 $-1$，$\mathtt{count\_le}(-1)$ 需返回 0

- **状态设计冗余**：含一些"实际无用的维度"会让记忆化数组爆炸——状态设计要"既覆盖全部约束、又不冗余"

## 相关例题

- [洛谷P2657 [SCOI2009] windy 数](https://www.luogu.com.cn/problem/P2657)

- [洛谷P2602 [ZJOI2010] 数字计数](https://www.luogu.com.cn/problem/P2602)

- [洛谷P4127 [AHOI2009] 同类分布](https://www.luogu.com.cn/problem/P4127)

- [洛谷P4124 [CQOI2016] 手机号码](https://www.luogu.com.cn/problem/P4124)

- [洛谷P6218 [USACO06NOV] Round Numbers S](https://www.luogu.com.cn/problem/P6218)

$\blacksquare$