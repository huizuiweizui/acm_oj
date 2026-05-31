#难度/★★★★★

> 当 dp 转移是**线性递推**——$f[n]$ 是 $f[n-1], f[n-2], \ldots$ 的线性组合——把状态压成向量、转移压成矩阵，再用 [[矩阵快速幂]] 把 $O(n)$ 加速到 $O(\log n)$。$n \le 10^{18}$ 也能秒过。

## 前置知识

- [[矩阵快速幂]]

- [[快速幂]]

- [[线性dp]]

## 核心思想

很多 [[线性dp]] 的转移有形式——

$$f[n] = c_1 f[n-1] + c_2 f[n-2] + \cdots + c_k f[n-k]$$

朴素 $O(n)$ 推到 $f[n]$；但当 $n = 10^{18}$ 时 $10^{18}$ 步必定 TLE。**关键观察**：上式右侧是 $f[n-1], \ldots, f[n-k]$ 的**线性组合**——可以写成矩阵乘法！

把"状态"压成长度 $k$ 的向量——

$$\vec{v}_n = \begin{pmatrix} f[n] \\ f[n-1] \\ \vdots \\ f[n - k + 1] \end{pmatrix}$$

构造**转移矩阵** $M$（$k \times k$），使——

$$\vec{v}_n = M \cdot \vec{v}_{n-1}$$

迭代展开 $\vec{v}_n = M^{n - k} \cdot \vec{v}_k$——一旦能 $O(\log n)$ 求 $M^{n-k}$，整个 dp 就 $O(\log n)$。

由于矩阵乘法满足**结合律**，可用 [[矩阵快速幂]] 在 $O(k^3 \log n)$ 完成。状态维度 $k$ 小（$\le 100$）时碾压朴素。

> 💡 **何时该想到矩阵快速幂**：
>
> - 转移是常系数线性递推（$f[n]$ 是若干 $f[n - j]$ 的固定线性组合）
>
> - $n$ 极大（$\ge 10^8$，朴素 $O(n)$ 不可承受）
>
> - 状态维度小（$\le 100$，否则 $O(k^3 \log n)$ 也吃不消）
>
> 满足这三条就该尝试矩阵化。

## 经典例题：Fibonacci 大数版

> 给定 $n \in [1, 10^{18}]$ 和素数 $p$，求 Fibonacci 数列的第 $n$ 项 $F_n \bmod p$，其中 $F_1 = F_2 = 1$、$F_i = F_{i-1} + F_{i-2}$（$i \ge 3$）。

**状态怎么想**：递推每次"读"前两项——把它们打包成向量是自然选择。

设——

$$\vec{v}_i = \begin{pmatrix} F_i \\ F_{i-1} \end{pmatrix}$$

**转移怎么推**：

$$\begin{gather}
F_i = F_{i-1} + F_{i-2} \\
F_{i-1} = F_{i-1}
\end{gather}$$

写成矩阵——

$$\begin{pmatrix} F_i \\ F_{i-1} \end{pmatrix} = \begin{pmatrix} 1 & 1 \\ 1 & 0 \end{pmatrix} \begin{pmatrix} F_{i-1} \\ F_{i-2} \end{pmatrix}$$

记 $M = \begin{pmatrix} 1 & 1 \\ 1 & 0 \end{pmatrix}$，迭代——

$$\vec{v}_n = M \vec{v}_{n-1} = M^2 \vec{v}_{n-2} = \cdots = M^{n - 2} \vec{v}_2$$

初始 $\vec{v}_2 = \begin{pmatrix} 1 \\ 1 \end{pmatrix}$。

**答案**：$\vec{v}_n$ 的第一个分量 = $(M^{n-2})_{1,1} \cdot 1 + (M^{n-2})_{1,2} \cdot 1$。

或者更简洁——直接观察 $M^n = \begin{pmatrix} F_{n+1} & F_n \\ F_n & F_{n-1} \end{pmatrix}$，所以 $F_n = (M^n)_{1, 2}$（用归纳法可证）。

**复杂度**：$O(2^3 \log n) = O(\log n)$。$n = 10^{18}$ 时 $\log n \approx 60$，瞬间。

> 💡 **构造转移矩阵的通法**：每行对应一个新状态分量——
>
> 1. $F_i$ 行：$F_i = 1 \cdot F_{i-1} + 1 \cdot F_{i-2}$ → 系数 $(1, 1)$
>
> 2. $F_{i-1}$ 行（搬移过来的，保留）：$F_{i-1} = 1 \cdot F_{i-1} + 0 \cdot F_{i-2}$ → 系数 $(1, 0)$
>
> 把行系数堆起来即矩阵。任何线性递推都可这样构造。

## 适用场景

- 常系数线性递推、$n$ 极大、状态维度小

- 经典模型：广义 Fibonacci、循环节、状态有限的字符串自动机 dp（结合 [[KMP]] / [[AC自动机]]）

- 图上"恰好 $k$ 步路径计数"——邻接矩阵的 $k$ 次幂

- 图上"恰好 $k$ 步最短路"——$(\min, +)$ 半环下的矩阵幂

- 部分概率 dp、计数 dp 的状态压缩后续

- 不适用：递推非线性（含 $f[n-1]^2$ 等非线性项）；递推系数随 $n$ 变化（矩阵会因 $n$ 而异，无法快速幂）；状态维度过大

## 步骤拆解

1. **判断线性可矩阵化**：转移是否可表为 "$\vec{v}_n = M \vec{v}_{n-1}$"，其中 $M$ 与 $n$ 无关

2. **设状态向量**：$\vec{v}_i$ 包含 $f[i]$ 及之前 $k - 1$ 项（或额外辅助分量）

3. **构造转移矩阵 $M$**：每行写一条线性等式的系数

4. **计算 $M^p$**（$p$ 由 $n$ 推出）：用矩阵快速幂 $O(k^3 \log n)$

5. **乘上初始向量**：得到目标向量 $\vec{v}_n$，提取所需分量

## 代码模板

**模板：Fibonacci 大数版**

```cpp

class fib_matrix {

private:

    using Mat = vector<vector<long long>>;

    long long MOD;

    Mat mul(const Mat& A, const Mat& B) {

        int n = (int)A.size();

        int m = (int)B[0].size();

        int p = (int)B.size();

        Mat C(n, vector<long long>(m, 0));

        for (int i = 0; i < n; i++) {

            for (int k = 0; k < p; k++) {

                if (A[i][k] == 0) continue;             // 稀疏优化

                for (int j = 0; j < m; j++) {

                    C[i][j] = (C[i][j] + A[i][k] * B[k][j]) % MOD;

                }

            }

        }

        return C;

    }

    Mat mat_pow(Mat A, long long e) {

        int n = (int)A.size();

        Mat R(n, vector<long long>(n, 0));

        for (int i = 0; i < n; i++) R[i][i] = 1;        // 单位矩阵

        while (e > 0) {

            if (e & 1) R = mul(R, A);

            A = mul(A, A);

            e >>= 1;

        }

        return R;

    }

public:

    fib_matrix(long long MOD_in) {

        MOD = MOD_in;

    }

    long long solve(long long n) {

        if (n <= 2) return 1 % MOD;

        Mat M = {{1, 1}, {1, 0}};

        Mat P = mat_pow(M, n - 2);

        // v_2 = (1, 1)，v_n = P * v_2，取第一行

        long long fn = (P[0][0] * 1 + P[0][1] * 1) % MOD;

        return fn;

    }

};
```

> ⚠️ **取模在每次乘法之后**：矩阵元素相乘可能爆 `long long`——`A[i][k] * B[k][j]` 若两者都到 $10^9$，乘积达 $10^{18}$ 接近 `long long` 上限。安全做法是每步 `(A[i][k] * B[k][j]) % MOD` 后再加。

> 💡 **稀疏矩阵优化**：`if (A[i][k] == 0) continue;` 在含许多 0 的转移矩阵上能加速一倍以上。状态自动机类问题中矩阵常常稀疏。
## 复杂度分析

- 时间复杂度：$O(k^3 \log n)$

  - 单次矩阵乘 $O(k^3)$（$k$ 是矩阵维度）

  - 快速幂迭代 $O(\log n)$ 次

- 空间复杂度：$O(k^2)$（存矩阵）

> 💡 **典型量级**：$k = 2, n = 10^{18}$ 时 $\log n \approx 60$、$k^3 = 8$——总 $480$ 次乘加，瞬间。$k = 100, n = 10^{18}$ 时 $6 \times 10^7$，几秒内可解。

## 正确性证明

### 转移矩阵的存在性

**命题**：若递推 $f[n] = \sum_{i=1}^{k} c_i f[n - i]$（$c_i$ 是常数），则存在 $k \times k$ 矩阵 $M$ 使 $\vec{v}_n = M \vec{v}_{n-1}$。

**证明**：构造——

$$M = \begin{pmatrix} c_1 & c_2 & \cdots & c_{k-1} & c_k \\ 1 & 0 & \cdots & 0 & 0 \\ 0 & 1 & \cdots & 0 & 0 \\ \vdots & \vdots & \ddots & \vdots & \vdots \\ 0 & 0 & \cdots & 1 & 0 \end{pmatrix}$$

矩阵第 1 行是递推系数；其余行是单位偏移（把 $f[n-i]$ 搬到 $f[n - i - 1]$ 的位置）。

直接验证 $M \vec{v}_{n-1}$ 的第 $i$ 个分量——

- 第 1 个分量：$\sum_{j=1}^{k} c_j f[n - j] = f[n]$ ✓

- 第 $i$ 个分量（$i \ge 2$）：第 $i$ 行只有第 $(i-1)$ 列为 1，乘出 $f[n - 1 - (i - 2)] = f[n - i + 1]$ ✓

所以 $M \vec{v}_{n-1} = \vec{v}_n$。$\blacksquare$

### 矩阵快速幂的正确性

由矩阵乘法**结合律** $M(MN) = (MM)N$，对幂指数 $e$ 二进制分解 $e = \sum_i b_i 2^i$ 得——

$$M^e = \prod_i M^{2^i b_i}$$

每次平方得到 $M^{2^{i+1}}$，对每个 $b_i = 1$ 的位累乘——总迭代 $O(\log e)$。详细证明见 [[矩阵快速幂]] 与 [[快速幂]]。$\blacksquare$

### 初始向量与目标分量

**命题**：$\vec{v}_n = M^{n - k} \vec{v}_k$，其中 $\vec{v}_k = (f[k], f[k-1], \ldots, f[1])^T$。

**证明**：归纳。$\vec{v}_k = \vec{v}_k = M^0 \vec{v}_k$ 平凡。假设 $\vec{v}_{n-1} = M^{n-1-k} \vec{v}_k$，则——

$$\vec{v}_n = M \vec{v}_{n-1} = M \cdot M^{n-1-k} \vec{v}_k = M^{n - k} \vec{v}_k$$

由归纳成立。$\blacksquare$

## 应用扩展

### 应用一：图上 $k$ 步路径计数

> 给一张 $n$ 个点的有向图（邻接矩阵 $A$），求恰好走 $k$ 步从 $u$ 到 $v$ 的不同路径数。

**结论**：路径数 $= (A^k)_{u, v}$。

**证明**：归纳。$(A^1)_{u, v} = A_{u, v}$（边数）即长 1 路径数。归纳——

$$(A^{k+1})_{u, v} = \sum_w (A^k)_{u, w} \cdot A_{w, v}$$

右侧含义：枚举长 $k+1$ 路径的倒数第二个点 $w$——前 $k$ 步从 $u$ 到 $w$ 共 $(A^k)_{u, w}$ 条，最后一步 $w \to v$ 取决于边 $A_{w, v}$。求和即长 $k+1$ 路径数。$\blacksquare$

$k$ 大且需要"恰好 $k$ 步"的路径数时，用矩阵快速幂——$O(n^3 \log k)$。

### 应用二：$(\min, +)$ 半环——图上 $k$ 步最短路

> 求图上**恰好经过 $k$ 条边**的最短 $u \to v$ 路径长度。

普通矩阵乘法 $(A B)_{i, j} = \sum_k A_{i, k} B_{k, j}$ 中——把 $\sum$ 换成 $\min$、$\times$ 换成 $+$，定义"广义乘法"——

$$(A \otimes B)_{i, j} = \min_k (A_{i, k} + B_{k, j})$$

**关键性质**：这个广义乘法仍**满足结合律**——所以快速幂仍适用！

把图的邻接矩阵 $D$（边权矩阵，无边 = $+\infty$）按 $(\min, +)$ 求 $D^k$——$(D^k)_{u, v}$ 即"恰好 $k$ 条边的最短 $u \to v$ 路径长度"。

> 💡 **广义半环的本质**：矩阵乘法所需的代数结构是"半环"——只要"$+$" 满足结合律（且有零元）、"$\times$" 满足结合律（且有幺元）、且 $\times$ 对 $+$ 分配——快速幂就成立。$(\min, +)$、$(\max, +)$、$(\text{or}, \text{and})$ 都是合法半环。

### 应用三：状态自动机 dp

> 求长 $n$ 的字符串中**不含**某个固定模式串 $P$ 的字符串数。$n \le 10^{18}$、$|P| \le 100$。

**状态**：[[KMP]] 失配自动机的当前状态（"$P$ 当前已匹配前缀长度"）。

转移矩阵 $M$ 中 $M[s][s'] =$ "从自动机状态 $s'$ 添加一字符后转移到 $s$ 且**不达到完整匹配**的字符数"——

- $M$ 维度 = $|P|$

- $n$ 步后状态分布 = $M^n \vec{v}_0$

每个分量的和 = 所求字符串数。结合 [[AC自动机]] 可以处理多模式串。

### 应用四：广义 Fibonacci / 含常数项

若递推含**常数项**——如 $f[n] = f[n-1] + f[n-2] + 7$——把常数 $7$ 也作为一个状态分量。新状态向量 $\vec{v}_n = (f[n], f[n-1], 1)^T$，转移矩阵——

$$M = \begin{pmatrix} 1 & 1 & 7 \\ 1 & 0 & 0 \\ 0 & 0 & 1 \end{pmatrix}$$

最后一行的"$1$"列保证常数项始终为 1，第一行的 7 列把这个常数加进 $f[n]$。

这个技巧扩展到任何含**多项式形式的非齐次项**：$f[n] = \cdots + n + 5$ 时把 $n$ 与 $1$ 都加入状态。

## 几个常见错误

- **下标偏移搞错**：初始向量是 $\vec{v}_k$（第 $k$ 个状态），$M$ 的指数是 $n - k$。$k$ 是递推阶数而不是 $f$ 的最小下标——很容易错位 1

- **取模忘记每步加**：$(\text{大数} \cdot \text{大数})$ 超 `long long`——每次乘法后立即取模

- **构造矩阵时行列搞反**：$M \vec{v}$ 的约定下，矩阵的**第 $i$ 行**是计算 $\vec{v}_n$ 第 $i$ 个分量的系数。如果用 $\vec{v}^T M$ 的约定则相反

- **稀疏忽略**：转移矩阵很多 0 时常数很差——加 `if (A[i][k] == 0) continue;` 能显著加速

- **$(\min, +)$ 半环忘了改恒等元**：$(\min, +)$ 中的"$0$"（零元）是 $+\infty$，"$1$"（幺元）是 $0$——单位矩阵的对角线应填 $0$、非对角线填 $+\infty$

- **快速幂指数为 0 的边界**：$M^0$ 是单位矩阵，对应"不走任何步、$\vec{v}_k$ 本身"——别少写

## 相关例题

- [洛谷P1962 斐波那契数列](https://www.luogu.com.cn/problem/P1962)

- [洛谷P1939 [模板] 矩阵加速（数列）](https://www.luogu.com.cn/problem/P1939)

- [洛谷P3216 [HNOI2011] 数学作业](https://www.luogu.com.cn/problem/P3216)

- [洛谷P2233 [HNOI2002] 公交车路线](https://www.luogu.com.cn/problem/P2233)

- [洛谷P4159 [SCOI2009] 迷路](https://www.luogu.com.cn/problem/P4159)

- [洛谷P3758 [TJOI2017] 可乐](https://www.luogu.com.cn/problem/P3758)

- [洛谷P5343 [SDOI2018] 物理实验](https://www.luogu.com.cn/problem/P5343)

$\blacksquare$