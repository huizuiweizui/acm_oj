#难度/★★★

> 一棵以"字符"为边的多叉树，把字符串集合按公共前缀压缩存储，支持 $O(L)$ 的插入和查询。

## 定义与特性

- **本质**：多叉树（通常 26 叉处理小写字母，10 叉处理数字，2 叉处理二进制位）

- **核心性质**：从根到任意节点的路径上的字符拼成一个**前缀**——所有共享前缀的字符串在 Trie 中共享前缀路径

- **存储方式**：每个节点维护一个孩子数组（如 `children[26]`）以及一些标志（是否是某字符串的终止节点、计数等）

- **不变量**：树中每条根到叶的完整路径对应集合中的某个字符串

## 操作与复杂度

记字符集大小为 $\Sigma$，单次操作字符串长度为 $L$：

| 操作               | 时间复杂度                    | 说明                       |
| ---------------- | ------------------------ | ------------------------ |
| 插入字符串            | $O(L)$                   | 沿字符路径走，缺失则新建             |
| 查询某字符串是否存在       | $O(L)$                   | 沿路径走，路径中断则不存在            |
| 查询前缀计数           | $O(L)$                   | 走到对应节点读出计数               |
| 空间消耗             | $O(\sum L \cdot \Sigma)$ | 每节点开 $\Sigma$ 个孩子指针      |

## 实现方式

**经典模板：处理小写英文字母字符串集合**：

```cpp

class trie {

private:

    vector<vector<int>> children;   // children[u][c] = 节点 u 沿字符 c 走到的孩子节点编号

    vector<int> end_count;          // end_count[u] = 以 u 为终止节点的字符串个数

    int tot;                        // 节点总数

    int new_node() {

        children.push_back(vector<int>(26, 0));

        end_count.push_back(0);

        tot += 1;

        return tot;

    }

public:

    trie() {

        tot = 0;

        new_node();                 // 新建根节点（编号 1），0 号位作"空指针"

    }

    void insert(const string& s) {

        int u = 1;                  // 从根开始

        for (char ch : s) {

            int c = ch - 'a';

            if (children[u][c] == 0) {

                int v = new_node();

                children[u][c] = v;

            }

            u = children[u][c];

        }

        end_count[u] += 1;

    }

    // 查询字符串 s 是否存在（出现次数）
    int count(const string& s) {

        int u = 1;

        for (char ch : s) {

            int c = ch - 'a';

            if (children[u][c] == 0) {

                return 0;

            }

            u = children[u][c];

        }

        return end_count[u];

    }

    // 查询有多少字符串以 s 为前缀
    bool has_prefix(const string& s) {

        int u = 1;

        for (char ch : s) {

            int c = ch - 'a';

            if (children[u][c] == 0) {

                return false;

            }

            u = children[u][c];

        }

        return true;

    }

};
```

> 💡 **节点编号约定**：用 `0` 表示空指针（不存在的孩子），实际节点编号从 `1` 开始，所以 `children[u][c] == 0` 就表示该方向的孩子不存在。

> 💡 **vector vs. 静态数组**：`vector<vector<int>>` 写起来直观，按需扩展。卡常题可以预先 `reserve` 或改用预分配数组。

## 内部原理

**为什么共享前缀能省空间**：考虑字符串集合 `{"apple", "app", "apply", "ape"}`，朴素存储要存 4 串字符共 17 字节。Trie 中它们共享前缀 `"ap"`，再共享 `"app"`，最终的树形如：

```
        root

         |

         a

         |

         p

        / \

       e   p — *(end of "app")

       *   |

           l

          / \

         e   y

         *   *
```

只需存少量节点和"终止标记"即可。前缀重复越多，越省空间。

**为什么 $O(L)$ 操作**：每次操作都是从根开始沿字符路径走 $L$ 步，每步是 $O(1)$ 数组访问。

**Trie 的三种典型变形**：

| 变种             | 字符集大小    | 典型应用                     |
| -------------- | -------- | ------------------------ |
| 普通 Trie        | 26 / 256 | 字符串集合查询、前缀统计             |
| **01-Trie**    | 2        | 维护整数集合，求异或最值/异或对计数       |
| **可持久化 Trie**  | 2 / 26   | 维护历史版本，可查询某段时间内的字符串集     |

**01-Trie 的妙用**：把每个数字拆成 32 位二进制，从高位到低位插入。对于"找一个数 $y$ 使 $x \oplus y$ 最大"的问题，从根开始**贪心地走与 $x$ 当前位相反的方向**——若不存在则被迫走相同方向。这能在 $O(\log V)$ 内得到答案。

## 适用场景

- 字符串集合的快速插入、查询、前缀统计

- 词典自动补全的底层结构

- IP 路由表（前缀匹配）

- 01-Trie 求异或最值（最大/最小异或对）

- [[AC自动机]] 的基础（Trie + 失配指针）

- 不适用：字符集太大（需要改用哈希 + map）；需要排序遍历（用平衡树或排序）

## 相关例题

- [洛谷P8306 【模板】字典树](https://www.luogu.com.cn/problem/P8306)

- [洛谷P4551 最长异或路径](https://www.luogu.com.cn/problem/P4551)

$\blacksquare$