#难度/★

> 求两个数的最大公约数（Greatest Common Divisor）和最小公倍数（Least Common Multiple），是数论的基础。

## 前置知识

- [[模运算]]

## 核心思想

**GCD（欧几里得算法 / 辗转相除法）**：基于关键定理

$$\gcd(a, b) = \gcd(b, a \bmod b)$$

不断用余数替换被除数，问题规模迅速缩小，直到 $b = 0$ 时，$a$ 即为 gcd。

**LCM**：由两数关系直接推出

$$\text{lcm}(a, b) = \frac{a \cdot b}{\gcd(a, b)}$$

为避免 `a * b` 溢出，实际计算时写成 `a / gcd(a, b) * b` —— **先除后乘**。

## 适用场景

- 各种涉及"整除"、"约分"、"周期"的问题

- 求 [[组合数]] 时的约分

- [[中国剩余定理]]、扩展欧几里得等数论算法的基础

## 步骤拆解

**GCD**：

1. 当 $b \ne 0$ 时，记 $t = a \bmod b$

2. 令 $a \leftarrow b$，$b \leftarrow t$

3. 循环结束后返回 $a$

**LCM**：先求 $\gcd$，再算 $\dfrac{a}{\gcd(a,b)} \cdot b$。

## 代码模板

```cpp
// 最大公约数
long long gcd(long long a, long long b) {

    while (b != 0) {

        long long t = a % b;

        a = b;

        b = t;

    }

    return a;

}

// 最小公倍数
long long lcm(long long a, long long b) {

    return a / gcd(a, b) * b;

}
```

> 💡 C++17 起 `<numeric>` 头文件提供 `std::gcd` 和 `std::lcm`，比赛允许时直接用即可。

## 复杂度分析

- 时间复杂度：$O(\log \min(a, b))$

- 空间复杂度：$O(1)$

## 正确性证明

**欧几里得定理**：$\gcd(a, b) = \gcd(b, a \bmod b)$。

**证明**：设 $a = qb + r$（其中 $r = a \bmod b$）。

- 任意 $a$ 和 $b$ 的公约数 $d$，由 $r = a - qb$ 可知 $d \mid r$，故 $d$ 也是 $b$ 和 $r$ 的公约数。

- 反之，任意 $b$ 和 $r$ 的公约数 $d$，由 $a = qb + r$ 可知 $d \mid a$，故 $d$ 也是 $a$ 和 $b$ 的公约数。

两组公约数集合相同，故最大公约数也相同。$\blacksquare$

**LCM 公式**：$a \cdot b = \gcd(a, b) \cdot \text{lcm}(a, b)$。
**证明**：由唯一分解定理可证。

- 对每个质因子 $p$，设 $v_p(a) = \alpha$、$v_p(b) = \beta$。

- 则 $v_p(\gcd) = \min(\alpha, \beta)$、$v_p(\text{lcm}) = \max(\alpha, \beta)$。

- 而 $\min + \max = \alpha + \beta$，所以 $\gcd \cdot \text{lcm} = a \cdot b$。$\blacksquare$

## 相关例题

- [洛谷P1029 最大公约数和最小公倍数](https://www.luogu.com.cn/problem/P1029)