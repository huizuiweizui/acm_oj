
> 这一篇不是算法笔记——是一份"复杂模拟、字符串、大整数场景下用 Python 的速查清单"。所有代码默认 Python 3.9；高于 3.9 的特性单独标注。

> 💡 **何时该用 Python**：题目以模拟为主、字符串操作复杂、需要任意精度整数、或者只想验证 C++ 答案——这些场景下 Python 写起来比 C++ 快几倍。

---

## 0. 默认设置（赛前模板）

```python

import sys

from collections import defaultdict, Counter, deque

from heapq import heappush, heappop, heapify

from functools import lru_cache, cache, reduce

from itertools import permutations, combinations, product, accumulate

from bisect import bisect_left, bisect_right, insort

from math import gcd, lcm, isqrt, comb, perm, inf, factorial

input = sys.stdin.readline                       # 输入加速

sys.setrecursionlimit(10**6)                     # 默认 1000，递归题必加

def solve():

    n = int(input())

    a = list(map(int, input().split()))

    # ...

solve()

```

> 💡 **`input = sys.stdin.readline`**：内置 `input()` 慢 5-10 倍，竞赛标配重定向。注意 `readline()` 包含末尾 `\n`，整数 `int()` 转换会自动处理，但作为字符串使用时记得 `.strip()`。

> ⚠️ **`sys.setrecursionlimit`**：Python 默认递归深度仅 1000，DFS / 记忆化搜索很容易爆栈。

---

## 1. 输入输出 / 性能

### 快速读入

```python

import sys

input = sys.stdin.readline

n = int(input())

a = list(map(int, input().split()))             # 一行 n 个整数

# 多行整数矩阵
matrix = [list(map(int, input().split())) for _ in range(n)]

# 单字符串
s = input().strip()                              # 注意 strip 去 '\n'

# 一次读入全部输入（最快）
data = sys.stdin.read().split()

# 然后用迭代器消费
it = iter(data)

n = int(next(it))

a = [int(next(it)) for _ in range(n)]

```

### 快速输出

```python

# 大量输出时用 sys.stdout.write
import sys

output = sys.stdout.write

output(str(ans) + '\n')

# 收集后一次输出
results = []

for _ in range(q):

    results.append(str(query()))

print('\n'.join(results))

# print 的便利参数
print(1, 2, 3)                                   # 1 2 3

print(1, 2, 3, sep=',')                          # 1,2,3

print('no newline', end='')                      # 不换行

print(*[1, 2, 3])                                # 1 2 3（解包打印）

```

> 💡 **拼接成大字符串一次性输出**：循环里 `print` 比 `'\n'.join(...)` 慢一个量级。$10^5$ 行输出时差距明显。

### f-string（格式化）

```python

x, y = 3, 4

f"x={x}, y={y}"                                  # 'x=3, y=4'

# 浮点保留小数
pi = 3.14159265358979

f"{pi:.4f}"                                      # '3.1416'

f"{pi:.4e}"                                      # '3.1416e+00'

# 整数格式
f"{255:b}"                                       # '11111111'（二进制）

f"{255:o}"                                       # '377'（八进制）

f"{255:x}"                                       # 'ff'（十六进制）

# 字段宽度
f"{42:5d}"                                       # '   42'

f"{42:05d}"                                      # '00042'

f"{'hi':>10}"                                    # '        hi'（右对齐）

f"{'hi':<10}"                                    # 'hi        '

f"{'hi':^10}"                                    # '    hi    '

# 千分位逗号
f"{1234567:,}"                                   # '1,234,567'

# Python 3.8+ 的调试形式
x = 42

f"{x=}"                                          # 'x=42'

```

---

## 2. 字符串

### 切片大法

```python

s = "abcdefgh"

s[0]                                             # 'a'

s[-1]                                            # 'h'（最后一个）

s[2:5]                                           # 'cde'

s[:3]                                            # 'abc'

s[3:]                                            # 'defgh'

s[::2]                                           # 'aceg'（每隔一个）

s[::-1]                                          # 'hgfedcba'（反转！）

s[1::2]                                          # 'bdfh'（奇数下标）

```

> 💡 **字符串反转**：是 Python 经典一行——比 C++ 的 `reverse(s.begin(), s.end())` 短得多。

### 查找与判断

```python

s = "abcabc"

s.find("bc")                                     # 1（首次出现，不存在返回 -1）

s.rfind("bc")                                    # 4

s.index("bc")                                    # 1（不存在抛 ValueError）

s.count("bc")                                    # 2（出现次数，不重叠）

s.startswith("abc")                              # True

s.endswith("bc")                                 # True

s.startswith(("a", "b"))                         # True（可传 tuple）

"hello" in s                                     # False（in 运算）

```

### 拆分与拼接

```python

"a,b,c".split(",")                             # ['a', 'b', 'c']

"  hello world  ".split()                      # ['hello', 'world']（默认按任意空白）

"a,,b".split(",")                              # ['a', '', 'b']（保留空串）

"a,b,c".split(",", 1)                          # ['a', 'b,c']（最多拆 1 次）

"line1\nline2\n".splitlines()                  # ['line1', 'line2']

",".join(["a", "b", "c"])                      # 'a,b,c'

"".join(["a", "b", "c"])                       # 'abc'

" ".join(str(x) for x in [1, 2, 3])            # '1 2 3'

```

> ⚠️ `"".join(list)` 比循环 `s += ...` 快很多——字符串不可变，循环拼接是 $O(n^2)$。

### 去空白 / 大小写

```python

"  hello  ".strip()                              # 'hello'

"  hello  ".lstrip()                             # 'hello  '

"  hello  ".rstrip()                             # '  hello'

"xxhelloxx".strip("x")                           # 'hello'（指定字符）

"Hello".lower()                                  # 'hello'

"Hello".upper()                                  # 'HELLO'

"Hello".swapcase()                               # 'hELLO'

"hello world".title()                            # 'Hello World'

"hello world".capitalize()                       # 'Hello world'

```

### 替换与去前后缀

```python

"abcabc".replace("b", "B")                       # 'aBcaBc'（替换全部）

"abcabc".replace("b", "B", 1)                    # 'aBcabc'（最多 1 次）

# Python 3.9+
"hello.txt".removeprefix("hello")                # '.txt'

"hello.txt".removesuffix(".txt")                 # 'hello'

```

### 字符判断

```python

"abc".isalpha()                                  # True

"123".isdigit()                                  # True

"abc123".isalnum()                               # True

"   ".isspace()                                  # True

"Hello".istitle()                                # True

ord('a')                                         # 97

chr(97)                                          # 'a'

```

### 填充

```python

"42".zfill(5)                                    # '00042'（前补 0）

"42".rjust(5, '0')                               # '00042'（同上）

"42".rjust(5)                                    # '   42'（默认空格）

"42".ljust(5, '-')                               # '42---'

"42".center(7, '*')                              # '**42***'

```

### 字符映射（批量替换）

```python

# 把所有元音替换为 '*'
table = str.maketrans("aeiou", "*****")

"hello world".translate(table)                   # 'h*ll* w*rld'

# 删除特定字符
table = str.maketrans("", "", "aeiou")

"hello world".translate(table)                   # 'hll wrld'

```

---

## 3. 列表

### 切片（同字符串）

```python

a = [1, 2, 3, 4, 5]

a[::-1]                                          # [5, 4, 3, 2, 1]（反转）

a[1:4]                                           # [2, 3, 4]

a[::2]                                           # [1, 3, 5]

a[:] = []                                        # 清空（原地）

```

### 增删改

```python

a = [1, 2, 3]

a.append(4)                                      # [1, 2, 3, 4]

a.extend([5, 6])                                 # [1, 2, 3, 4, 5, 6]（合并另一个列表）

a += [7, 8]                                      # 等价 extend

a.insert(1, 99)                                  # [1, 99, 2, 3, 4, 5, 6, 7, 8]

a.pop()                                          # 弹出末尾，返回弹出的值

a.pop(0)                                         # 弹出首位（O(n)！）

a.remove(3)                                      # 删除第一个等于 3 的元素

del a[0]                                         # 按下标删除

a.clear()                                        # 清空

```

> ⚠️ **`list.pop(0)` 是 $O(n)$**——要从队首弹用 `collections.deque`！

### 查询

```python

a = [1, 2, 3, 2, 1]

a.index(2)                                       # 1（首个 2 的下标，不存在抛异常）

a.count(2)                                       # 2

3 in a                                           # True（O(n)）

# 找最大/最小值的下标
a.index(max(a))                                  # 2

max(range(len(a)), key=lambda i: a[i])           # 同上

# 反向找
len(a) - 1 - a[::-1].index(2)                    # 最后一个 2 的下标

```

### 排序

```python

a = [3, 1, 4, 1, 5, 9, 2, 6]

a.sort()                                         # 原地升序

a.sort(reverse=True)                             # 原地降序

b = sorted(a)                                    # 返回新列表（不修改 a）

# 自定义键
words = ["abc", "ab", "abcd"]

words.sort(key=len)                              # 按长度

words.sort(key=lambda s: (len(s), s))            # 多关键字：先长度、再字典序


# 复杂对比（C++ 中的 cmp）
from functools import cmp_to_key

a.sort(key=cmp_to_key(lambda x, y: x - y))       # 升序

# 排序时附带原下标
indexed = sorted(enumerate(a), key=lambda x: x[1])

```

> 💡 **`sort()` 与 `sorted()` 的区别**：`sort()` 原地修改、无返回值（返回 `None`）；`sorted()` 返回新列表、可处理任何可迭代对象。

### 反转

```python

a.reverse()                                      # 原地反转

b = list(reversed(a))                            # 返回新迭代器（用 list 实例化）

b = a[::-1]                                      # 切片反转，最常用

```

### 推导式 / 生成器

```python

# 列表推导

squares = [x * x for x in range(10)]             # [0, 1, 4, 9, ..., 81]

evens = [x for x in range(20) if x % 2 == 0]

pairs = [(i, j) for i in range(3) for j in range(3)]

# 字典推导
d = {x: x * x for x in range(5)}                 # {0:0, 1:1, 2:4, 3:9, 4:16}

# 集合推导
s = {x % 3 for x in range(10)}                   # {0, 1, 2}

# 生成器（不实际生成列表，节省内存）
g = (x * x for x in range(10**9))                # 大数据时用

sum(x * x for x in range(100))                   # sum 接受生成器

```

> 💡 **推导式比 `for` + `append` 快**——CPython 内部有专门优化。

### 一些惯用法

```python

# 二维数组初始化

n, m = 3, 4

grid = [[0] * m for _ in range(n)]               # ✓ 三行四列、独立

grid = [[0] * m] * n                             # ✗ 所有行是同一引用！

# grid[0][0] = 1 会同时改变所有行的第 0 列

# 转置矩阵

matrix = [[1, 2, 3], [4, 5, 6]]

list(zip(*matrix))                               # [(1, 4), (2, 5), (3, 6)]

# 转成列表的列表：

[list(row) for row in zip(*matrix)]

# 顺时针 90 度旋转

[list(row) for row in zip(*matrix[::-1])]

# 解构赋值

a, b = 1, 2

a, b = b, a                                      # 交换（一行搞定）

# 多重解构

a, *rest = [1, 2, 3, 4]                          # a=1, rest=[2, 3, 4]

*head, tail = [1, 2, 3, 4]                       # head=[1, 2, 3], tail=4

first, *mid, last = [1, 2, 3, 4]                 # first=1, mid=[2, 3], last=4

```

### `enumerate` / `zip`

```python

for i, x in enumerate(["a", "b", "c"]):

    print(i, x)                                  # 0 a / 1 b / 2 c

for i, x in enumerate(["a", "b"], start=1):

    print(i, x)                                  # 1 a / 2 b

# 多列表并行遍历
for x, y in zip([1, 2, 3], ['a', 'b', 'c']):

    print(x, y)

# 不等长 zip（短的为准）
list(zip([1, 2, 3], [10, 20]))                   # [(1, 10), (2, 20)]

```

---

## 4. 字典

### 基础

```python

d = {"a": 1, "b": 2}

d["c"] = 3

d.get("c", -1)                         # 3

d.get("z", -1)                         # -1（默认值，不会报错）

# 安全获取或设置

d.setdefault("c", 0)                   # c 存在则返回 d["c"]，不存在则设为 0 后返回 0

# 遍历

for k in d: ...

for k, v in d.items(): ...

for v in d.values(): ...

# 是否存在

"a" in d                                         # True（查 key）

1 in d.values()                                  # True（查 value，O(n)）

# 删除

del d["a"]

d.pop("a", None)                                 # 不存在不报错（第二参为默认值）

```

### 合并字典

```python

a = {"x": 1, "y": 2}

b = {"y": 3, "z": 4}

# Python 3.5+：解包合并

{**a, **b}                                       # {'x':1, 'y':3, 'z':4}（b 覆盖 a）

# Python 3.9+：| 运算符

a | b                                            # 同上

a |= b                                           # 原地合并

```

> ⚠️ **Python 3.7+ 普通 dict 保持插入顺序**——以前要用 `OrderedDict`，现在不必。

---

## 5. 集合

```python

s = {1, 2, 3}

s = set([1, 2, 3])                               # 同上

s = set()                                        # 空集（{}是空字典！）

s.add(4)

s.remove(4)                                      # 不存在抛异常

s.discard(4)                                     # 不存在不报错

# 集合运算
a = {1, 2, 3}

b = {2, 3, 4}

a | b                                            # {1, 2, 3, 4}（并）

a & b                                            # {2, 3}（交）

a - b                                            # {1}（差）

a ^ b                                            # {1, 4}（对称差）

a <= b                                           # 子集

a < b                                            # 真子集

a >= b                                           # 超集

# frozenset：不可变集合，可作为 dict 的 key 或 set 的元素
fs = frozenset([1, 2, 3])

```

---

## 6. `collections` 模块

### `Counter`（计数神器）

```python

from collections import Counter

c = Counter("hello")                   # Counter({'l': 2, 'h': 1, 'e': 1, 'o': 1})

c = Counter([1, 1, 2, 3, 3, 3])        # Counter({3: 3, 1: 2, 2: 1})

c.most_common(2)                       # [(3, 3), (1, 2)]：前 2 高频

c.most_common()                        # 全部按频次降序

c["x"]                                 # 0（不存在不报错，返回 0）

c["a"] += 1                            # 直接加

# 算术运算
Counter("aab") + Counter("abc")        # Counter({'a': 3, 'b': 2, 'c': 1})

Counter("aabbcc") - Counter("abc")     # Counter({'a': 1, 'b': 1, 'c': 1})

```

### `defaultdict`（自动初始化）

```python

from collections import defaultdict

d = defaultdict(int)                             # 默认 0

d["a"] += 1                                      # 不报错（普通 dict 会 KeyError）

  

d = defaultdict(list)                            # 默认空列表

d["x"].append(1)                                 # 不报错

  

d = defaultdict(lambda: -1)                      # 默认 -1

```

### `deque`（双端队列）

```python

from collections import deque

dq = deque([1, 2, 3])

dq.append(4)                                     # 末尾加：[1, 2, 3, 4]

dq.appendleft(0)                                 # 首部加：[0, 1, 2, 3, 4]

dq.pop()                                         # 弹末尾，返回 4

dq.popleft()                                     # 弹首部，返回 0（O(1)！）

  

dq.rotate(1)                                     # 整体右移一位

dq.rotate(-1)                                    # 整体左移一位

  

dq = deque(maxlen=3)                             # 固定长度：满了后从另一端挤出

dq.append(1); dq.append(2); dq.append(3); dq.append(4)

# dq = deque([2, 3, 4])

```

> 💡 **BFS / 单调队列必备**：`list.pop(0)` 是 $O(n)$，`deque.popleft()` 是 $O(1)$。

### `OrderedDict`

```python

from collections import OrderedDict

# Python 3.7+ 普通 dict 已保持插入顺序，OrderedDict 现在主要用于以下场景：

od = OrderedDict()

od.move_to_end("a")                              # 把 key "a" 移到末尾

od.popitem(last=False)                           # 弹出首位（dict.popitem 只能弹末尾）

```

### `namedtuple`

```python

from collections import namedtuple

Point = namedtuple("Point", ["x", "y"])

p = Point(1, 2)

p.x, p.y                                         # 1 2

p[0], p[1]                                       # 1 2（也支持下标）

p._asdict()                                      # {'x': 1, 'y': 2}

p._replace(x=10)                                 # Point(x=10, y=2)（返回新对象）

```

---

## 7. `heapq`（堆 / 优先队列）

```python

from heapq import heappush, heappop, heapify, nlargest, nsmallest

# Python 的 heapq 是小根堆

h = []

heappush(h, 3)

heappush(h, 1)

heappush(h, 4)

heappop(h)                                       # 1（最小值）

h[0]                                             # 3（当前最小值，不弹出）

# 从已有列表建堆
a = [3, 1, 4, 1, 5, 9, 2]

heapify(a)                                       # 原地堆化，O(n)


# nlargest / nsmallest
nlargest(3, a)                                   # [9, 5, 4]

nsmallest(3, a)                                  # [1, 1, 2]

nlargest(3, a, key=lambda x: -x)                 # 自定义键

```

### 大根堆？取负数即可

```python

# 大根堆模拟

h = []

heappush(h, -3); heappush(h, -1); heappush(h, -4)

-heappop(h)                                      # 4（最大值）

# 自定义对象排序：用 tuple 第一项作为 key

# 如 (priority, item)

heappush(h, (3, "task A"))

heappush(h, (1, "task B"))

heappop(h)                                       # (1, 'task B')

```

> ⚠️ **元素是 tuple 时同优先级会比较后续字段**——若后续字段不可比较（如对象），用 `(priority, counter, item)` 加唯一计数器避免冲突。

---

## 8. `itertools`（迭代器工具）

```python

from itertools import permutations, combinations, product, accumulate, chain, groupby

# 排列：n! 种

list(permutations([1, 2, 3]))

# [(1, 2, 3), (1, 3, 2), (2, 1, 3), (2, 3, 1), (3, 1, 2), (3, 2, 1)]

list(permutations([1, 2, 3], 2))                 # 长度 2 的排列

# 组合：C(n, k) 种

list(combinations([1, 2, 3, 4], 2))

# [(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)]

# 笛卡尔积

list(product([1, 2], ['a', 'b']))

# [(1, 'a'), (1, 'b'), (2, 'a'), (2, 'b')]

list(product([0, 1], repeat=3))                  # 所有 3 位二进制：8 个 tuple

# [(0,0,0), (0,0,1), ..., (1,1,1)]

# 前缀和 / 累积

list(accumulate([1, 2, 3, 4]))                   # [1, 3, 6, 10]

list(accumulate([1, 2, 3, 4], initial=0))        # [0, 1, 3, 6, 10]（Python 3.8+）

list(accumulate([3, 1, 4, 1, 5], max))           # [3, 3, 4, 4, 5]（前缀最大值）

# 拼接

list(chain([1, 2], [3, 4], [5]))                 # [1, 2, 3, 4, 5]

# 按 key 分组（要求已排序）

data = [(1, 'a'), (1, 'b'), (2, 'c'), (2, 'd')]

for k, group in groupby(data, key=lambda x: x[0]):

    print(k, list(group))                        # 1 [(1,'a'), (1,'b')] / 2 [...]

```

### 其他常用

```python

from itertools import count, cycle, repeat, combinations_with_replacement, islice

count(10, 2)                                     # 10, 12, 14, ...（无限）

cycle([1, 2, 3])                                 # 1, 2, 3, 1, 2, 3, ...（无限）

repeat(5, 3)                                     # 5, 5, 5（重复 3 次）

# 可重复组合
list(combinations_with_replacement([1, 2, 3], 2))

# [(1,1), (1,2), (1,3), (2,2), (2,3), (3,3)]

# 取无限迭代器的前几项
list(islice(count(0, 2), 5))                     # [0, 2, 4, 6, 8]

```

---

## 9. `functools`

### `@lru_cache` / `@cache`（记忆化）

```python

from functools import lru_cache, cache

@lru_cache(maxsize=None)                         # 旧版写法

def fib(n):

    if n < 2: return n

    return fib(n - 1) + fib(n - 2)

@cache                                           # Python 3.9+，等价于 lru_cache(maxsize=None)

def fib(n):

    if n < 2: return n

    return fib(n - 1) + fib(n - 2)

fib(100)                                         # 瞬间出结果

fib.cache_clear()                                # 清缓存

fib.cache_info()                                 # 缓存统计信息

```

> 💡 **记忆化搜索神器**：把朴素 $O(2^n)$ 递归秒变 $O(n)$ dp。但参数必须 hashable（不能是 list / dict）——用 tuple / frozenset 替代。

### `reduce`

```python

from functools import reduce

reduce(lambda x, y: x + y, [1, 2, 3, 4])         # 10（等价于 sum）

reduce(lambda x, y: x * y, [1, 2, 3, 4])         # 24（连乘）

reduce(lambda x, y: x * y, [1, 2, 3, 4], 100)    # 2400（带初值）

```

### `cmp_to_key`

```python

from functools import cmp_to_key

# 当你想用 C++ 风格的 cmp 函数排序时

def cmp(a, b):

    return a - b                                 # 返回负 / 0 / 正 决定先后

sorted([3, 1, 4, 1, 5], key=cmp_to_key(cmp))     # [1, 1, 3, 4, 5]

```

### `partial`（偏函数）

```python

from functools import partial

def power(base, exp):

    return base ** exp

square = partial(power, exp=2)

square(5)                                        # 25

```

---

## 10. 数学（`math` + 内置）

### 内置数学函数

```python

abs(-5)                                      # 5

abs(-3.14)                                   # 3.14

abs(3 - 4j)                                  # 5.0（复数模长）

max(1, 2, 3)

max([1, 2, 3])

max([1, 2, 3], default=-1)                   # 列表空时返回默认值

min([(1, 'a'), (2, 'b')], key=lambda x: x[0])

sum([1, 2, 3])                               # 6

sum([1, 2, 3], 100)                          # 106（带初值）

# 整除与取模
divmod(17, 5)                                # (3, 2)：商和余数

# 三参数 pow——模幂！
pow(2, 100, 1000000007)                      # (2^100) mod p，比 (2**100) % p 快

pow(3, -1, 7)                                # 3 关于模 7 的逆元 = 5（Python 3.8+）

# 进制转换
bin(10)                                      # '0b1010'

oct(10)                                      # '0o12'

hex(255)                                     # '0xff'

int('ff', 16)                                # 255

int('1010', 2)                               # 10
```

> 💡 **`pow(a, b, m)` 是 Python 自带的模幂**——比手写快速幂更短，且 C 实现极快。

### `math` 模块

```python
import math

math.gcd(12, 18)                          # 6

math.lcm(12, 18)                          # 36（Python 3.9+）

math.gcd(*[12, 18, 24])                   # 6（多参数版本，Python 3.9+）

math.factorial(10)                        # 3628800

math.comb(5, 2)                           # 10：C(5, 2)（Python 3.8+）

math.perm(5, 2)                           # 20：P(5, 2)（Python 3.8+）

math.isqrt(10)                            # 3（整数平方根，Python 3.8+）

math.sqrt(2)                              # 1.4142135623730951

math.log(math.e)                          # 1.0（自然对数）

math.log2(1024)                           # 10.0

math.log10(100)                           # 2.0

math.floor(3.7)                           # 3

math.ceil(3.2)                            # 4

round(3.5)                                # 4（注意：Python 用 banker's rounding！）

round(2.5)                                # 2（不是 3！）

math.inf                                  # 正无穷大

math.nan                                  # NaN

math.pi                                   # 3.141592653589793

math.e                                    # 2.718281828459045
```

> ⚠️ **`round(2.5) = 2`**：Python 的 `round` 用银行家舍入（向偶数舍入）。要 C++ 风格的"逢 5 进 1" 用 `math.floor(x + 0.5)`。

---

## 11. `bisect`（有序列表的二分）

```python

from bisect import bisect_left, bisect_right, insort, insort_left

a = [1, 2, 3, 3, 3, 4, 5]                        # 已排序

bisect_left(a, 3)                                # 2（首个 >= 3 的位置）

bisect_right(a, 3)                               # 5（首个 > 3 的位置）

bisect_right(a, 3) - bisect_left(a, 3)           # 3 的个数 = 3

# 插入保持有序
a = [1, 3, 5, 7]

insort(a, 4)                                     # a 变成 [1, 3, 4, 5, 7]（O(n)！）

```

> ⚠️ **`insort` 是 $O(n)$**——因为列表插入要移动后续元素。要 $O(\log n)$ 的有序插入用 `SortedList`（见下文）。

### `SortedList`（来自第三方库 `sortedcontainers`，洛谷支持）

```python

from sortedcontainers import SortedList

sl = SortedList()

sl.add(3); sl.add(1); sl.add(5)                  # 自动保持有序

sl[0]                                            # 1（最小）

sl[-1]                                           # 5（最大）

sl.bisect_left(3)                                # 1（rank）

sl.remove(3)                                     # 删除一个

sl.pop(0)                                        # 弹出最小

```

`SortedList` 内部用分块跳跃表实现——增删查改全 $O(\log n)$。Python 的 set 不支持"求第 k 大"，这玩意补上了。

> ⚠️ **`sortedcontainers` 不是标准库**——在 Codeforces / 洛谷 上可用，本地可能要 `pip install sortedcontainers`。

---

## 12. 大整数 / 高精度

Python 的 `int` **原生支持任意精度**——直接算就行，永远不溢出。

```python

2 ** 1000                                        # 直接得到 302 位的整数

math.factorial(100)                              # 158 位整数

10 ** 100 + 1                                    # 没问题

# 大整数 GCD / 模幂
gcd(10**100, 10**100 + 1)                        # 1

pow(2, 10**18, 10**9 + 7)                        # 模幂，超快

```

> 💡 **这是 Python 在算法竞赛中的最大优势之一**——C++ 写高精度要几十行，Python 一行搞定。

---

## 13. 类型注解（可选，不影响运行）

```python

# Python 3.9+ 可以直接用内置容器作为泛型

def add(a: int, b: int) -> int:

    return a + b

def process(items: list[int]) -> dict[str, int]:  # Python 3.9+

    return {"sum": sum(items)}

# Python 3.8 及以前要写 typing.List[int]、typing.Dict[str, int]

```

---

## 14. 与 C++ 的"等价对"速查

| C++                 | Python                            |
| ------------------- | --------------------------------- |
| `vector<int>`       | `list`                            |
| `set<int>`          | `set`（无序）/ `SortedList`（有序）       |
| `map<K, V>`         | `dict`                            |
| `unordered_map`     | `dict`（Python 的 dict 本来就是 hash 表） |
| `multiset`          | `Counter` 或 `SortedList`          |
| `priority_queue<T>` | `heapq`（小根堆，大根用负数）                |
| `deque<int>`        | `collections.deque`               |
| `bitset`            | `int`（位运算）或 `bytearray`           |
| `pair<A, B>`        | `tuple` 或 `(a, b)`                |
| `tuple<A, B, C>`    | `tuple`                           |
| `sort()`            | `list.sort()` / `sorted()`        |
| `lower_bound`       | `bisect.bisect_left`              |
| `upper_bound`       | `bisect.bisect_right`             |
| `next_permutation`  | `itertools.permutations`（一次性出全部）  |
| `__gcd(a, b)`       | `math.gcd(a, b)`                  |
| `pow(a, b) % m` 快速幂 | `pow(a, b, m)`（内置！）               |
| `to_string(x)`      | `str(x)`                          |
| `stoi(s)`           | `int(s)`                          |
| `cin >> x`          | `int(input())`                    |

---

## 15. Python 3.10+ 特性（标注版本）

### 模式匹配 `match-case`（Python 3.10+）

```python

def parse(cmd):

    match cmd.split():

        case ["quit"]:

            return "bye"

        case ["move", direction]:

            return f"moving {direction}"

        case ["set", key, value]:

            return f"set {key}={value}"

        case _:

            return "unknown"

```

### 类型联合 `X | Y`（Python 3.10+）

```python

def f(x: int | str) -> None:                     # 等价于 Union[int, str]

    print(x)

```

### 多上下文管理器（Python 3.10+）

```python

with (open("a.txt") as fa, open("b.txt") as fb):

    ...

```

### 字典 `keys()` 的 `mapping` 属性（Python 3.10+）

```python

d = {"a": 1, "b": 2}

d.keys().mapping == d                            # True

```

---

## 16. Python 3.11+ 特性

### `Self` 类型注解

```python

from typing import Self                          # Python 3.11+

class Node:

    def clone(self) -> Self:

        ...

```

### 错误信息更精确（无需代码改动）

```python

# Python 3.11+ 错误指向具体表达式

# 例如 a["b"]["c"]["d"] 报错时会告诉你是哪一个 [] 出错

```

### `tomllib`

```python

import tomllib                                   # Python 3.11+

# 标准库支持 TOML 解析（之前要装 tomli）

```

---

## 17. 性能优化

### Python 慢的常见原因 + 加速技巧

```python

# 1. 局部变量比全局变量快

def hot_loop():

    local_sum = sum                              # 把内置函数缓存为局部变量

    for x in big_list: ...

# 2. 用 list comprehension 代替 for + append

result = [f(x) for x in data]                    # 比循环 + append 快

# 3. 用 dict / set 而不是 list 做 "存在判断"

if x in big_set:    # O(1)

if x in big_list:   # O(n)

# 4. 用 join 代替循环字符串拼接

"".join(parts)      # O(n)

s = ""

for p in parts: s += p      # O(n^2)，巨慢

# 5. 用 sys.stdin 代替 input

input = sys.stdin.readline   # 加速 5-10 倍

# 6. 计算密集型用 numpy（若题目允许）

import numpy as np

a = np.array(data)

np.sum(a ** 2)              # 比纯 Python 的列表推导快

# 7. PyPy

# 若 Codeforces / 洛谷 允许 PyPy，提交 PyPy3 而非 Python3——通常快 5-10 倍

```

### 全局变量陷阱

```python

counter = 0

def inc():

    counter += 1                                 # UnboundLocalError！

def inc():

    global counter

    counter += 1                                 # ✓

```

闭包 + 嵌套函数下用 `nonlocal`：

```python

def outer():

    x = 0

    def inner():

        nonlocal x

        x += 1

    inner()

    return x

```

---

## 18. 容易踩的坑

1. **`list.pop(0)` 是 $O(n)$**——用 `deque.popleft()` 替代

2. **`int(input())` 慢**——大量输入用 `sys.stdin.readline`

3. **递归限制 1000**——记得 `sys.setrecursionlimit(10**6)`

4. **`[[0] * m] * n` 是浅拷贝**——所有行是同一引用，用 `[[0]*m for _ in range(n)]`

5. **`round(2.5)` 返回 2** ——银行家舍入；要"逢 5 进 1" 用 `int(x + 0.5)`

6. **可变默认参数陷阱**：

   ```python

   def f(a=[]):                                  # ✗ 所有调用共享同一个列表！

       a.append(1)

       return a

   def f(a=None):                                # ✓

       if a is None: a = []

       ...

   ```

7. **字典 / 集合不能用可变对象作 key**——用 tuple / frozenset

8. **`copy` 浅深之分**：

   ```python

   import copy

   shallow = a.copy()                            # 或 a[:] / list(a)

   deep = copy.deepcopy(a)                       # 嵌套结构才需要

   ```

9. == vs `is`**：== 比较值；`is` 比较身份（同一对象）。`None` 用 `is`：`x is None`

10. **整数除法**：`/` 永远返回 float；要整除用 `//`

11. **负数取模**：`-7 % 3 = 2`（Python 与 C++ 不同！结果与除数同号）

12. **递归调用闭包修改外部变量要 `nonlocal`**——否则会创建新局部变量

13. **`for x in list:` 中修改 list**——迭代器失效。用 `for x in list[:]:` 或重新遍历

14. **生成器只能消费一次**——`g = (x*x for x in r)` 之后再次遍历得到空

15. **`sort` 与 `sorted` 区别**：前者无返回值（返回 `None`），错用会赋值得到 None

---

## 19. 实用代码片段
### 矩阵翻转 / 旋转

```python

matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

# 转置
list(zip(*matrix))                               # [(1,4,7), (2,5,8), (3,6,9)]

# 上下翻转
matrix[::-1]

# 左右翻转
[row[::-1] for row in matrix]

# 顺时针 90 度
[list(row) for row in zip(*matrix[::-1])]

# [[7,4,1], [8,5,2], [9,6,3]]

# 逆时针 90 度
[list(row) for row in zip(*matrix)][::-1]

```

### 二分模板

```python

# 二分答案

lo, hi = -1, n

while lo + 1< hi:

    mid = (lo + hi) // 2

    if check(mid):

        hi = mid

    else:

        lo = mid

return lo

```

### 最大公约数 / 模逆元

```python

from math import gcd

gcd(*[12, 18, 24])                               # 6（Python 3.9+ 多参数）

# 扩展欧几里得（求模逆元，3.8+ 也可以用 pow(a, -1, m)）
pow(3, -1, 7)                                    # 5（3 关于模 7 的逆元）

# 自己写扩展欧几里得
def extgcd(a, b):

    if b == 0: return a, 1, 0

    g, x, y = extgcd(b, a % b)

    return g, y, x - (a // b) * y

```

### 前缀和

```python

from itertools import accumulate

a = [1, 2, 3, 4]

ps = list(accumulate(a, initial=0))              # [0, 1, 3, 6, 10]（Python 3.8+）

# 区间 [l, r] 之和：ps[r+1] - ps[l]

```

### 一次读取所有输入

```python

import sys

data = sys.stdin.buffer.read().split()

idx = 0

def read_int():

    global idx

    idx += 1

    return int(data[idx - 1])

n = read_int()

a = [read_int() for _ in range(n)]

```

### 离散化

```python

a = [100, 50, 200, 50, 100]

sorted_unique = sorted(set(a))                   # [50, 100, 200]

mapper = {v: i for i, v in enumerate(sorted_unique)}

discretized = [mapper[x] for x in a]             # [1, 0, 2, 0, 1]

```

### 多关键字排序

```python

items = [(3, "a"), (1, "b"), (3, "z"), (1, "a")]

items.sort(key=lambda x: (x[0], x[1]))           # 先按第一关键字、再第二

items.sort(key=lambda x: (x[0], -ord(x[1][0])))  # 第二关键字降序

```

### 计时（卡常 / 调试用）

```python

import time

t0 = time.time()

print(f"Time: {time.time() - t0:.3f}s")

# 更精确
import time

t0 = time.perf_counter()

# ...

print(f"{time.perf_counter() - t0:.6f}s")

```

---

> 📌 **使用建议**：Python 在竞赛中常作为 **C++ 的补充**——拿来处理复杂字符串、大整数、暴力模拟。性能敏感的题仍优先 C++；但凡题目让 Python 也能在时限内通过，Python 写出的代码通常短一半、bug 少一半。