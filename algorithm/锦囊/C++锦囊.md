
> 这不是算法笔记——是一份"竞赛中容易遗忘但常用"的标准库 / GCC 扩展速查清单。所有代码默认 `using namespace std`、GCC 11、C++17；需要更高版本的特性会单独标注。

---

## 0. 默认设置（赛前模板）

```cpp

#include <bits/stdc++.h>                // GCC 扩展：一次包含所有标准库头

using namespace std;

  

int main() {

    ios::sync_with_stdio(false);        // 取消 C/C++ IO 同步

    cin.tie(nullptr);                   // 取消 cin/cout 绑定

    cout << fixed << setprecision(10);  // 浮点保留 10 位小数

  

    // ... 你的代码

    return 0;

}

```

> 💡 `<bits/stdc++.h>` 是 GCC 私货——竞赛常用、生产代码不推荐。其他编译器（MSVC/Clang 部分版本）不一定支持，但 GCC / Codeforces / 洛谷等全支持。

---

## 1. 输入输出 / 格式化

### 加速 IO

```cpp

ios::sync_with_stdio(false);    // ⚠️ 调用后不能再用 scanf/printf！

cin.tie(nullptr);

```

提速效果：`cin >> x` 从 ~$10^7$/s 提到 ~$10^8$/s，与 `scanf` 相当。

### 浮点输出（`<iomanip>`）

```cpp

double x = 3.14159265358979;

cout << fixed << setprecision(4) << x;          // 3.1416

cout << scientific << setprecision(3) << x;     // 3.142e+00

cout << defaultfloat << setprecision(6) << x;   // 3.14159（重置为默认）

```

- `fixed`：小数点后**固定** $k$ 位

- `defaultfloat`：总有效位数 $k$ 位（默认 6）

- `scientific`：科学计数法

### 整数进制

```cpp

cout << hex << 255;             // ff

cout << oct << 8;               // 10

cout << dec << 10;              // 10（恢复十进制）

cout << showbase << hex << 255; // 0xff

cout << uppercase << hex << 255;// FF

```

### 字段宽度 / 填充字符

```cpp

cout << setw(5) << 3;                       // "    3"

cout << setfill('0') << setw(4) << 5;       // "0005"

cout << left << setw(5) << "hi" << "|";     // "hi   |"

```

### 布尔输出

```cpp

cout << boolalpha << true;      // "true"（默认是 "1"）

cout << noboolalpha << true;    // "1"

```

### 字符串读取

```cpp

string s;

cin >> s;           // 读单 token，遇空白停止

getline(cin, s);    // 读整行，遇 '\n' 停止

```

> ⚠️ **混用 `>>` 和 `getline` 的坑**：

```cpp
int n;

cin >> n;           // 留下 '\n' 在缓冲区

getline(cin, s);    // 立刻读到空行！

cin.ignore();       // 加这句吃掉 '\n'

getline(cin, s);    // 现在 OK
```

---

## 2. 二分查找（`<algorithm>`）

### `lower_bound` / `upper_bound`

```cpp

vector<int> v = {1, 2, 3, 3, 3, 4, 5};

auto p = lower_bound(v.begin(), v.end(), 3);  // 第一个 >= 3 的位置（值为 3）

auto q = upper_bound(v.begin(), v.end(), 3);  // 第一个 > 3 的位置（值为 4）

int cnt = q - p;                              // 3 的出现次数 = 3

int idx = p - v.begin();                      // 转下标

```

数组也行：

```cpp

int a[] = {1, 3, 5, 7, 9};

int *p = lower_bound(a, a + 5, 5);            // 指向 5

int idx = p - a;                              // 2

```

带比较器：

```cpp

// 在降序数组中查找

vector<int> v = {9, 7, 5, 3, 1};

auto p = lower_bound(v.begin(), v.end(), 5, greater<int>());

```

> ⚠️ **要求数组有序**——默认升序，或符合传入比较器的顺序。

### `binary_search` / `equal_range`

```cpp

bool found = binary_search(v.begin(), v.end(), 3);  // true / false（不返回位置）

auto [lo, hi] = equal_range(v.begin(), v.end(), 3); // = {lower_bound, upper_bound}

```

### ⚠️ set/map 上的二分要用成员函数

```cpp

set<int> s = {1, 3, 5};

auto it1 = s.lower_bound(3);                          // ✓ O(log n)

auto it2 = lower_bound(s.begin(), s.end(), 3);        // ✗ O(n)！

```

`std::lower_bound` 用的随机访问迭代器在 set/map 上退化为 $O(n)$。

---

## 3. 字符串（`<string>`）

### `substr`

```cpp

string s = "abcdefgh";

s.substr(2);        // "cdefgh"（从位置 2 到末尾）

s.substr(2, 3);     // "cde"（从位置 2 取 3 个字符）

```

### `find` 系列

```cpp

string s = "abcabc";

s.find("bc");          // 1（首次出现）

s.find("bc", 3);       // 4（从位置 3 开始找）

s.rfind("bc");         // 4（最后一次出现）

s.find('z');           // string::npos（未找到）

if (s.find("xyz") == string::npos) { /* 不存在 */ }

s.find_first_of("aeiou");          // 第一个属于该集合的字符位置

s.find_first_not_of(" \t\n");      // 第一个非空白字符

s.find_last_of("xyz");

```

### 字符串与数字互转

```cpp

int n = stoi("123");           // 123

long long ll = stoll("123456789012");

double d = stod("3.14");

unsigned long u = stoul("123");

string s1 = to_string(123);    // "123"

string s2 = to_string(3.14);   // "3.140000"

```

> ⚠️ `stoi` 在不能转换时抛 `invalid_argument` / `out_of_range`。C++17 有更稳的 `from_chars`（不抛异常、更快）。

### 大小写转换

```cpp

#include <algorithm>

#include <cctype>

string s = "Hello";

transform(s.begin(), s.end(), s.begin(), ::tolower);  // "hello"

transform(s.begin(), s.end(), s.begin(), ::toupper);  // "HELLO"

```

### 拼接 / 插入 / 替换

```cpp

string a = "hello";

a += " world";                  // "hello world"

a.append(3, '!');               // "hello world!!!"

string b = "hello world";

b.replace(6, 5, "C++");         // "hello C++"（从位置 6 替换 5 个字符）

b.insert(5, " there");          // 在位置 5 插入

b.erase(0, 6);                  // 删除 [0, 6)

b.pop_back();                   // 删末尾字符

```

### C++20: `starts_with` / `ends_with`（需 `-std=c++20`，GCC 11 支持）

```cpp

string s = "hello.txt";

s.starts_with("hello");         // true

s.ends_with(".txt");            // true

```

> ⚠️ C++23 的 `contains` GCC 11 **不支持**——用 `find != npos` 替代。

---

## 4. 排序与排列（`<algorithm>`）

### `sort` 家族

```cpp

sort(v.begin(), v.end());                        // 升序

sort(v.begin(), v.end(), greater<int>());        // 降序

sort(v.begin(), v.end(), [](int a, int b){

    return a > b;                                // lambda 比较器

});

stable_sort(v.begin(), v.end());                 // 稳定排序

partial_sort(v.begin(), v.begin() + k, v.end()); // 前 k 个最小、有序

nth_element(v.begin(), v.begin() + k, v.end());  // 第 k 小（O(n) 期望），前后无序

```

> ⚠️ 比较器**必须严格弱序**：用 `<=` 会 UB。`return a < b` 升序、`return a > b` 降序。

### `next_permutation` / `prev_permutation`

```cpp

vector<int> v = {1, 2, 3};

do {

    /* 处理排列 */

} while (next_permutation(v.begin(), v.end()));

// 枚举 {1,2,3}、{1,3,2}、{2,1,3}、{2,3,1}、{3,1,2}、{3,2,1}

```

> 💡 要枚举所有排列必须先排成**升序**起始；`prev_permutation` 方向相反。

### `unique`（去重）

```cpp

vector<int> v = {1, 1, 2, 2, 3, 3};

sort(v.begin(), v.end());                              // 必须先排序！

v.erase(unique(v.begin(), v.end()), v.end());          // v = {1, 2, 3}

```

`unique` 只去**相邻**重复——离散化的标准三步：`sort → unique → erase`。

### `reverse` / `rotate`

```cpp

reverse(v.begin(), v.end());

vector<int> v = {1, 2, 3, 4, 5};

rotate(v.begin(), v.begin() + 2, v.end());   // {3, 4, 5, 1, 2}

```

### `shuffle`

```cpp

#include <random>

mt19937 rng(42);

shuffle(v.begin(), v.end(), rng);

```

> ⚠️ `random_shuffle` 在 C++17 中**已弃用**、C++17 后被移除。一律用 `shuffle` + `mt19937`。

---

## 5. 数值算法（`<numeric>` / `<algorithm>`）

### `accumulate` / `iota`

```cpp

#include <numeric>

vector<int> v = {1, 2, 3, 4};

int sum = accumulate(v.begin(), v.end(), 0);              // 10

long long sum_ll = accumulate(v.begin(), v.end(), 0LL);   // 防溢出！

// 自定义二元运算
int prod = accumulate(v.begin(), v.end(), 1, multiplies<int>());

vector<int> w(5);

iota(w.begin(), w.end(), 1);                              // {1, 2, 3, 4, 5}

```

> ⚠️ **`accumulate` 的初值类型决定运算类型**：

```cpp

vector<double> d = {1.5, 2.5};

accumulate(d.begin(), d.end(), 0);    // 3（int 加！丢失小数）

accumulate(d.begin(), d.end(), 0.0);  // 4.0（正确）
```

### `partial_sum` / `adjacent_difference`

```cpp

vector<int> v = {1, 2, 3, 4};

vector<int> ps(4);

partial_sum(v.begin(), v.end(), ps.begin());          // {1, 3, 6, 10}：前缀和

vector<int> ad(4);

adjacent_difference(v.begin(), v.end(), ad.begin()); // {1, 1, 1, 1}：差分

```

### `min` / `max` / `minmax`

```cpp

min(3, 5);                                              // 3

max({1, 2, 3, 4, 5});                                   // 5（多参数版，C++11）

auto [lo, hi] = minmax({3, 1, 4, 1, 5});                // lo=1, hi=5

auto it_min = min_element(v.begin(), v.end());          // 迭代器

auto it_max = max_element(v.begin(), v.end());

auto [imin, imax] = minmax_element(v.begin(), v.end());

```

### `count` / `find` / `all_of` / `any_of` / `none_of`

```cpp

vector<int> v = {1, 2, 3, 2, 1};

int c = count(v.begin(), v.end(), 2);                              // 2

int c_even = count_if(v.begin(), v.end(), [](int x){return x % 2 == 0;});

auto it = find(v.begin(), v.end(), 3);                             // 找到则非 end()

auto it2 = find_if(v.begin(), v.end(), [](int x){return x > 2;});

bool all_pos = all_of(v.begin(), v.end(), [](int x){return x > 0;});

bool has_neg = any_of(v.begin(), v.end(), [](int x){return x < 0;});

bool no_zero = none_of(v.begin(), v.end(), [](int x){return x == 0;});

```

### `gcd` / `lcm`（C++17）

```cpp

#include <numeric>

gcd(12, 18);    // 6

lcm(12, 18);    // 36

```

GCC 扩展 `__gcd(a, b)` 也能用（但不在标准里）。

### 集合操作（要求有序）

```cpp

#include <algorithm>

vector<int> a = {1, 2, 3, 4}, b = {3, 4, 5, 6}, c;

set_union(a.begin(), a.end(), b.begin(), b.end(), back_inserter(c));

// c = {1, 2, 3, 4, 5, 6}

c.clear();

set_intersection(a.begin(), a.end(), b.begin(), b.end(), back_inserter(c));

// c = {3, 4}

c.clear();

set_difference(a.begin(), a.end(), b.begin(), b.end(), back_inserter(c));

// c = {1, 2}（a 中有、b 中没有的）

c.clear();

merge(a.begin(), a.end(), b.begin(), b.end(), back_inserter(c));

// c = {1, 2, 3, 3, 4, 4, 5, 6}（合并两个有序序列）

```

---

## 6. 容器与方法

### `set` / `multiset`（`<set>`）

```cpp

multiset<int> ms;

ms.insert(3); ms.insert(3); ms.insert(5);

ms.count(3);                  // 2

// ⚠️ 删除陷阱
ms.erase(3);                  // 删除所有 3！

ms.erase(ms.find(3));         // 只删一个 3

// 查找：用成员函数！
auto it = ms.find(3);          // 找不到返回 ms.end()

auto lo = ms.lower_bound(3);   // O(log n)

auto hi = ms.upper_bound(3);

ms.erase(lo, hi);              // 区间删除

// 反向遍历
for (auto it = ms.rbegin(); it != ms.rend(); ++it) ...

// 最小 / 最大
*ms.begin();        // 最小

*ms.rbegin();       // 最大（不用 max_element！）

```

> 💡 **`ms.erase(3)` vs `ms.erase(ms.find(3))`**：前者删所有等于 3 的、后者只删一个。`multiset` 这点最坑。

### `map` / `unordered_map`（`<map>` / `<unordered_map>`）

```cpp

map<string, int> mp;

mp["alice"] = 90;

mp.insert({"bob", 85});

mp.emplace("charlie", 70);              // 原地构造

// ⚠️ operator[] 会自动创建键
if (mp["dave"] > 0) { ... }             // dave 被默认构造为 0！

// 只查询用 count 或 find
if (mp.count("dave")) { ... }

if (auto it = mp.find("dave"); it != mp.end()) {

    use(it->second);

}

// 结构化绑定遍历（C++17）
for (auto& [name, score] : mp) { ... }

// at 不会创建，但不存在时抛 out_of_range
int x = mp.at("dave");                  // 抛异常
```

### `unordered_map` 防 hack

```cpp
// CF 等比赛中，unordered_map 易被构造数据 hack 到 O(n)

struct custom_hash {

    static uint64_t splitmix64(uint64_t x) {

        x += 0x9e3779b97f4a7c15;

        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9;

        x = (x ^ (x >> 27)) * 0x94d049bb133111eb;

        return x ^ (x >> 31);

    }

    size_t operator()(uint64_t x) const {

        static const uint64_t SEED =

            chrono::steady_clock::now().time_since_epoch().count();

        return splitmix64(x + SEED);

    }

};

unordered_map<int, int, custom_hash> mp;
```

### `priority_queue`（`<queue>`）

```cpp

priority_queue<int> pq;                  // 默认大根堆

pq.push(3); pq.push(1); pq.push(5);

pq.top();                                // 5

pq.pop();

// 小根堆
priority_queue<int, vector<int>, greater<int>> pq_min;

// 自定义比较
auto cmp = [](pair<int,int> a, pair<int,int> b) {

    return a.second > b.second;          // 按 second 升序

};

priority_queue<pair<int,int>, vector<pair<int,int>>, decltype(cmp)> pq2(cmp);
```

> ⚠️ **比较函数返回 `a < b` 反而是大根堆**——和 `sort` 相反，反直觉。记忆：`priority_queue` 中"优先级高"放队首，`a < b` 为真表示 `b` 更优先。

### `deque`（`<deque>`）

```cpp

deque<int> dq;

dq.push_back(1); dq.push_front(0); dq.push_back(2);   // {0, 1, 2}

dq.front(); dq.back();

dq.pop_front(); dq.pop_back();

dq[0];                                                 // 随机访问，O(1) 但常数大于 vector

```

### `vector` 容易遗忘的

```cpp

vector<int> v = {3, 1, 4};

v.assign(5, 0);                  // 重置为 {0, 0, 0, 0, 0}

v.emplace_back(7);               // 原地构造（构造复杂对象时比 push_back 快）

v.reserve(1000);                 // 预留容量、避免反复扩容

v.shrink_to_fit();               // 释放多余容量

v.data();                        // 原始指针（用于 C 风格接口）

// 在指定位置插入 / 删除
v.insert(v.begin() + 2, 99);

v.erase(v.begin() + 2);

v.erase(v.begin() + 1, v.begin() + 3);  // 区间 [1, 3)

```

### `array`（`<array>`）

```cpp

array<int, 5> arr = {1, 2, 3, 4, 5};

arr.size();        // 5（编译期已知）

arr.fill(0);       // 全填 0

sort(arr.begin(), arr.end());

```

固定长度数组的"现代版"——支持值传递、可作为返回值、`size()` 内嵌。

### `bitset`（`<bitset>`）

```cpp

bitset<32> bs(0b1010);

bs.count();         // 1 的个数

bs.any();           // 是否至少一个 1

bs.all();           // 是否全 1

bs.none();          // 是否全 0

bs.size();          // 32（编译期）

bs.set(2);          // 第 2 位置 1

bs.reset(2);        // 第 2 位置 0

bs.flip();          // 全部取反

bs.flip(2);         // 单位取反

bs[3];              // 访问（可读可写）

bs.to_string();     // "...01010"

bs.to_ulong();      // 转 unsigned long

bs.to_ullong();     // 转 unsigned long long

// 支持位运算
bitset<32> a, b;

auto c = a & b;     // 同样可用 | ^ ~ << >>

```

> 💡 **bitset 的"超速优势"**：长 $n$ 的 `bitset` 做位运算是 $O(n / 64)$，比手写 64 倍更快。背包可行性 / 字符串匹配等问题常用 bitset 优化。

---

## 7. 迭代器辅助（`<iterator>`）

  

```cpp

vector<int> v = {1, 2, 3, 4, 5};

auto it = v.begin();

advance(it, 3);              // it 指向 v[3]（修改 it）

auto it2 = next(it);         // 不修改 it，返回 it+1

auto it3 = next(it, 2);      // it + 2

auto it4 = prev(it);         // it - 1

distance(v.begin(), v.end());  // 5

// 反向迭代器
for (auto it = v.rbegin(); it != v.rend(); ++it) { ... }

// 插入迭代器
vector<int> dst;

copy(v.begin(), v.end(), back_inserter(dst));    // 等价于反复 push_back

```

---

## 8. 位运算工具

### GCC builtin（非标准但 GCC 全支持）

```cpp

__builtin_popcount(n);     // n 的二进制中 1 的个数（int）

__builtin_popcountll(n);   // long long 版

__builtin_clz(n);          // 前导 0 个数（int，n != 0）

__builtin_clzll(n);

__builtin_ctz(n);          // 末尾 0 个数（int，n != 0）

__builtin_ctzll(n);

__builtin_parity(n);       // 1 的个数的奇偶性

```

> ⚠️ **`n = 0` 时 `clz` / `ctz` 行为未定义**！调用前判断。

```cpp

// "n 的最高位是第几位"
int highbit = 31 - __builtin_clz(n);     // n > 0

// "n 是不是 2 的幂"
bool is_pow2 = n > 0 && (n & (n - 1)) == 0;

```

### C++20 `<bit>`（需 `-std=c++20`，GCC 11 支持）

```cpp

#include <bit>

popcount(n);          // 同 __builtin_popcount，无 UB

countl_zero(n);       // 前导 0

countr_zero(n);       // 末尾 0

bit_floor(n);         // 不超过 n 的最大 2 的幂

bit_ceil(n);          // 不小于 n 的最小 2 的幂

bit_width(n);         // 表示 n 所需位数

has_single_bit(n);    // 是否是 2 的幂

rotl(n, k); rotr(n, k); // 循环左/右移

```

---

## 9. 数学（`<cmath>`）

```cpp

sqrt(2.0);

cbrt(8.0);              // 立方根

pow(2, 10);             // 注意返回 double

exp(1);

log(2.7);               // 自然对数

log2(1024);             // 10

log10(100);             // 2

hypot(3, 4);            // sqrt(3^2 + 4^2) = 5（防溢出版）

abs(-5);                // 整数（int 版在 <cstdlib>，long long 版在 <cstdlib>/<cmath>）

fabs(-3.14);            // 浮点

floor(3.7);             // 3

ceil(3.2);              // 4

round(3.5);             // 4（四舍五入）

trunc(3.7);             // 3（向零取整）

fmod(7.5, 2.0);         // 1.5（浮点取模）

```

> ⚠️ **`pow(int, int)` 返回 double**——`pow(10, 9)` 可能因精度返回 `999999999.999`！整数幂用快速幂手写。

### `__int128`（GCC 扩展）

```cpp

__int128 x = (__int128)1e18 * 100;       // 不溢出

// 没有 cin/cout 重载——要自己写
void print(__int128 x) {

    if (x < 0) { putchar('-'); x = -x; }

    if (x > 9) print(x / 10);

    putchar('0' + x % 10);

}

```

---

## 10. 随机数（`<random>`）

```cpp

#include <random>
#include <chrono>

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// 或固定种子调试： mt19937 rng(42);

uniform_int_distribution<int> dist(1, 100);

int x = dist(rng);                       // [1, 100] 均匀分布

uniform_real_distribution<double> dist_d(0.0, 1.0);

double y = dist_d(rng);

mt19937_64 rng64(42);                    // 64 位版本

```

> ⚠️ **别用 `rand()`**——它的 `RAND_MAX` 可能只有 32767，且随机性差。`mt19937` 周期 $2^{19937} - 1$，竞赛标配。

---

## 11. C++17 关键特性

### 结构化绑定

```cpp

pair<int, int> p = {1, 2};

auto [x, y] = p;

map<string, int> mp;

for (auto& [key, val] : mp) { ... }

tuple<int, double, string> t = {1, 3.14, "hi"};

auto [a, b, c] = t;

// 数组也行
int arr[3] = {1, 2, 3};

auto& [x, y, z] = arr;

```

### `if` / `switch` 初始化语句

```cpp

if (auto it = mp.find(key); it != mp.end()) {

    use(it->second);

}                       // it 作用域到这里

switch (auto state = get_state(); state) {

    case 0: ...;

}
```

### `std::optional`（`<optional>`）

```cpp

optional<int> find_val(int key) {

    if (key < 0) return nullopt;

    return key * 2;

}

auto r = find_val(3);

if (r.has_value()) cout << *r;

if (r) cout << *r;                       // 同上

int v = r.value_or(-1);                  // 不存在时返回 -1

```

### `std::tuple` / `std::tie`（`<tuple>`）

```cpp

tuple<int, string, double> t(1, "hi", 3.14);

get<0>(t);                  // 1

get<string>(t);             // "hi"（按类型取，要求该类型唯一）

int a; string b; double c;

tie(a, b, c) = t;           // 解包

tie(a, ignore, c) = t;      // 忽略 b

```

### `std::pair` 比较

```cpp

pair<int, int> a = {1, 2}, b = {1, 3};

a < b;          // true（先比较 first，再比较 second）

```

可直接放进 `set` 排序、做字典序比较。

### lambda 表达式高级用法

```cpp

auto fact = [&](auto self, int n) -> int {       // 递归 lambda（C++14+）

    return n <= 1 ? 1 : n * self(self, n - 1);

};

fact(fact, 5);                                   // 120

// 捕获列表
int x = 10;

auto f1 = [x](int y) { return x + y; };          // 按值

auto f2 = [&x](int y) { x = y; };                // 按引用

auto f3 = [=](int y) { return x + y; };          // 按值捕获所有

auto f4 = [&](int y) { x = y; };                 // 按引用捕获所有

```

---

## 12. C++20 部分特性（需 `-std=c++20`，GCC 11 部分支持）

### 字符串 `starts_with` / `ends_with`

```cpp

string s = "hello.txt";

s.starts_with("hello");      // true

s.ends_with(".txt");         // true

// 注意：contains 是 C++23，GCC 11 不支持

```

### `std::span`（`<span>`）

```cpp

void process(span<int> data) {

    for (int x : data) cout << x;

}

int arr[] = {1, 2, 3};

vector<int> v = {4, 5, 6};

process(arr);                // 直接传数组

process(v);                  // 直接传 vector

```

> 视图类——既能传数组、又能传 vector，无拷贝。

### `std::ranges`（部分支持）

```cpp

#include <ranges>

vector<int> v = {1, 2, 3, 4, 5};

auto even = v | views::filter([](int x){ return x % 2 == 0; });

for (int x : even) cout << x;       // 2 4

```

### 其他 C++20 / C++23 GCC 11 状态

- `std::format`：**GCC 11 不完整**——要用 `<format>` 需 GCC 13+。竞赛中继续 `printf` / `stringstream`

- `std::bit_cast`、`<bit>`：GCC 11 支持

- 模块（`import`）：GCC 11 实验性支持，竞赛不推荐

- `std::print`（C++23）：GCC 11 不支持

---

## 13. GCC 扩展：policy-based 数据结构

### 有序统计树（"求第 k 大 / 求 rank"）

```cpp

#include <ext/pb_ds/tree_policy.hpp>

#include <ext/pb_ds/assoc_container.hpp>

using namespace __gnu_pbds;

typedef tree<

    int,                                 // 键类型

    null_type,                           // 值类型（null_type 表示集合）

    less<int>,                           // 比较器

    rb_tree_tag,                         // 红黑树

    tree_order_statistics_node_update    // 关键：支持排名查询

> ordered_set;

ordered_set os;

os.insert(3); os.insert(1); os.insert(5);

*os.find_by_order(0);        // 第 0 小（即最小）= 1

*os.find_by_order(2);        // 第 2 小 = 5

os.order_of_key(3);          // 严格小于 3 的元素数 = 1

```

> ⚠️ **pbds 的 `tree` 不允许重复键**——要存重复值用 `pair<value, id>` 加唯一标识。

### `gp_hash_table`（更快的 hash 表）

```cpp

#include <ext/pb_ds/assoc_container.hpp>

using namespace __gnu_pbds;

gp_hash_table<int, int> mp;

// 用法同 unordered_map，但常数小很多（无链表、用线性探测）

```

> ⚠️ CF 等比赛中 `unordered_map` 易被 hack，`gp_hash_table` + 自定义 hash 是更稳的选择。

---

## 14. 函数对象 / 仿函数（`<functional>`）

```cpp

#include <functional>

plus<int>()(3, 4);             // 7

minus<int>()(3, 4);            // -1

multiplies<int>()(3, 4);       // 12

divides<int>()(8, 2);          // 4

modulus<int>()(7, 3);          // 1

negate<int>()(5);              // -5

greater<int>()(3, 4);          // false

less<int>()(3, 4);             // true

equal_to<int>()(3, 3);         // true

bit_and<int>()(6, 3);          // 2

bit_or<int>()(6, 3);           // 7

bit_xor<int>()(6, 3);          // 5

```

可作为 STL 算法的比较器 / 二元操作：

```cpp

sort(v.begin(), v.end(), greater<int>());

accumulate(v.begin(), v.end(), 1, multiplies<int>());

priority_queue<int, vector<int>, greater<int>> pq_min;

```

---

## 15. 时间测量

```cpp

#include <chrono>

auto t0 = chrono::steady_clock::now();

// ... 代码 ...

auto t1 = chrono::steady_clock::now();

auto ms = chrono::duration_cast<chrono::milliseconds>(t1 - t0).count();

cout << "Time: " << ms << " ms\n";

```

竞赛中卡常 / 测速时用。

---

## 16. 容易踩的坑（汇总）

1. **`unordered_map` 易被 hack**：CF 中要用自定义 hash 或 `gp_hash_table`

2. **`sort` 比较器必须严格弱序**：`<=` 会 UB

3. **`size()` 是无符号**：`v.size() - 1` 当 `v` 为空时是巨大正数。比较时 `(int)v.size() - 1`

4. **`pow(int, int)` 返回 double**：精度坑——整数幂手写快速幂

5. **`__gcd` 不在标准里**：用 `gcd`（C++17）

6. **`map[]` 自动创建键**：只查询用 `find` 或 `count`

7. **set/map 上的 `lower_bound` 用成员函数**：用 `std::` 算法是 $O(n)$

8. **`multiset::erase(value)` 删全部，`erase(iterator)` 删一个**

9. **`stoi` 抛异常**：不能转换时要处理；高速度场景用 `from_chars`

10. **混用 `cin >>` 和 `getline` 留 '\n'**：中间加 `cin.ignore()`

11. **比较浮点要用 `abs(a - b) < eps`**：直接 == 几乎一定挂

12. **`priority_queue` 比较器方向反直觉**：`return a < b` 是大根堆

13. **循环里 `erase` 要用 `it = container.erase(it)`**：否则迭代器失效

14. **`accumulate` 初值类型决定运算类型**：用 `0LL`、`0.0` 防溢出 / 精度

15. **`bits/stdc++.h` 编译慢**：但竞赛中不在乎

16. **`__builtin_clz(0)` 是 UB**：使用前判断

17. **`vector<bool>` 不是真正的容器**：是位压缩的代理类型，引用语义诡异——存布尔用 `vector<char>`

18. **数组传参退化为指针**：`sizeof(arr) / sizeof(arr[0])` 在函数内是错的；要用 vector 或显式传长度

---

## 17. 几个实用片段

### 离散化

```cpp

vector<int> a, b;       // a 是原数组、b 是离散化辅助

b = a;

sort(b.begin(), b.end());

b.erase(unique(b.begin(), b.end()), b.end());

// 查询 a[i] 离散化后的值

for (int& x : a) x = lower_bound(b.begin(), b.end(), x) - b.begin() + 1;

```

### 多关键字排序

```cpp

struct Item { int a, b, c; };

vector<Item> v;

sort(v.begin(), v.end(), [](const Item& x, const Item& y) {

    if (x.a != y.a) return x.a < y.a;

    if (x.b != y.b) return x.b > y.b;      // 第二关键字降序

    return x.c < y.c;

});

```

或用 `tuple` 简化（按字典序，但只能升序）：

```cpp

sort(v.begin(), v.end(), [](const Item& x, const Item& y) {

    return tie(x.a, x.b, x.c) < tie(y.a, y.b, y.c);

});

```

### 反向遍历 + 索引

```cpp

for (int i = (int)v.size() - 1; i >= 0; i--) { ... }

// 或

for (auto it = v.rbegin(); it != v.rend(); ++it) { ... }

```

### 二分答案模板

```cpp

int l = -1, r = n;

while (l + 1< r) {

    int mid = l + (r - l) / 2;

    if (check(mid)) {
	    r = mid;
	} else {
		l = mid;
	}
}

return r;

```

> 详见 [[二分答案]]。

---

> 📌 **使用建议**：这份清单不必背——通读一遍知道"有这些东西"即可。写题时遇到具体需求回来查最快。