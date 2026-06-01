# 算法知识图谱 + AI 问答 实施计划

## 目标

1. **知识图谱**：把 62 个算法条目以图的形式可视化，节点是算法，边是"前置依赖/关联"关系，帮助学习者理解学习路径。
2. **AI 问答（RAG）**：把 `algorithm/` 目录下的 Markdown 笔记作为知识库，用户在算法详情页可以针对当前算法提问，也可以跨算法自由提问，AI 基于笔记内容回答。

---

## 第一步：知识图谱

### 1.1 边数据从哪来

| 来源 | 说明 | 工作量 |
|------|------|--------|
| Obsidian `[[链接]]` | `algorithm/` 中每篇笔记都有 `[[并查集]]`、`[[BFS]]` 等引用，解析后天然就是有向边 | 写一个解析脚本，自动提取 |
| 手动补充 | 少量重要关系（如"Dijkstra 依赖 堆"）用 JSON 手写补充 | 约 20~30 条 |
| 同分类软连接 | 同一 category 内的算法之间加一条"同类"虚线 | 自动生成 |

### 1.2 数据结构设计

在 `judge/models.py` 新增 `AlgorithmEdge` 模型：

```python
class AlgorithmEdge(models.Model):
    EDGE_TYPES = [
        ('prerequisite', '前置依赖'),   # A 是 B 的前置知识
        ('related',      '相关算法'),   # 同类、互为变种
        ('extends',      '扩展应用'),   # B 是 A 的进阶版本
    ]
    source = models.ForeignKey(Algorithm, related_name='out_edges', on_delete=models.CASCADE)
    target = models.ForeignKey(Algorithm, related_name='in_edges',  on_delete=models.CASCADE)
    edge_type = models.CharField(max_length=20, choices=EDGE_TYPES, default='related')

    class Meta:
        unique_together = ['source', 'target']
```

### 1.3 自动解析脚本

新建 `judge/management/commands/build_graph.py`，执行逻辑：

```
1. 遍历 algorithm/**/*.md
2. 提取文件名（去掉 .md）→ 作为节点标识
3. 正则匹配 [[目标名]] → 建立 (当前文件, 目标) 的有向边
4. 把目标名模糊匹配到 Algorithm.name 或 Algorithm.algo_id
5. 写入 AlgorithmEdge 表（source=当前, target=目标, type='related'）
6. 未能匹配的打印出来，手动处理
```

关键依赖关系手写进 `seed_edges.py`（约 30 条），示例：

```python
MANUAL_EDGES = [
    ('dijkstra',      'heap',         'prerequisite'),  # Dijkstra 需要堆
    ('kruskal',       'union-find',   'prerequisite'),  # Kruskal 需要并查集
    ('bitmask-dp',    'bitwise',      'prerequisite'),  # 状压DP 需要位运算
    ('segment-tree',  'divide-conquer','prerequisite'), # 线段树基于分治
    ('lca',           'dfs',          'prerequisite'),  # LCA 需要 DFS
    ('aho-corasick',  'trie',         'extends'),       # AC自动机扩展 Trie
    ('aho-corasick',  'kmp',          'extends'),       # AC自动机是 KMP 的多模版
    ('merge-sort',    'divide-conquer','extends'),
    ('quick-sort',    'divide-conquer','extends'),
    ('lis',           'binary-search','extends'),       # LIS O(nlogn) 用到二分
    ('matrix',        'fast-pow',     'prerequisite'),  # 矩阵快速幂
    ('floyd',         'dp-general',   'extends'),
    ('tree-dp',       'dfs',          'prerequisite'),
    ('tree-dp',       'dp-general',   'extends'),
    # ...
]
```

### 1.4 API 端点

在 `judge/api_urls.py` 新增：

```
GET /api/algorithms/graph/
```

返回格式：

```json
{
  "nodes": [
    { "id": "dijkstra", "name": "Dijkstra", "category": "图论",
      "difficulty": "进阶", "group": 5 }
  ],
  "edges": [
    { "source": "dijkstra", "target": "heap", "type": "prerequisite" }
  ]
}
```

`group` 是 category 的数字编号，供前端按分类着色。

### 1.5 前端实现

新建路由 `/learn/graph`，新建 `LearnGraphView.vue`。

使用 **ECharts Graph**（项目已引入 ECharts，无需新增依赖）：

```js
option = {
  series: [{
    type: 'graph',
    layout: 'force',         // 力导向布局，自动分散
    roam: true,              // 可缩放平移
    draggable: true,
    focusNodeAdjacency: true,// 悬停高亮邻居
    edgeSymbol: ['none', 'arrow'],
    categories: [            // 按 category 着色
      { name: '基础算法', itemStyle: { color: '#7c6af7' } },
      { name: '排序',    itemStyle: { color: '#22d3ee' } },
      // ...
    ],
    nodes: [...],  // 来自 API
    edges: [...],  // 来自 API
  }]
}
```

交互细节：
- 点击节点 → 跳转到 `/learn/<algo_id>` 详情页
- 悬停节点 → tooltip 显示算法名、分类、难度
- 右上角 category 筛选（隐藏/显示某分类节点）
- 难度滑块筛选（只显示"入门"或"入门+提高"）

---

## 第二步：AI 问答（RAG）

### 2.1 整体架构

```
用户提问
    │
    ▼
[Query Embedding]  ──── 调用 Claude / OpenAI Embedding API
    │
    ▼
[向量检索]  ──── 在预建的向量索引中找 top-k 最相关的笔记片段
    │
    ▼
[Prompt 组装]  ──── system + 检索到的原文片段 + 用户问题
    │
    ▼
[LLM 生成]  ──── 调用 Claude API
    │
    ▼
[流式返回]  ──── SSE 推送到前端，逐字打印
```

### 2.2 知识库建设

**文档来源**：`algorithm/**/*.md` 下所有 Markdown 文件（约 80+ 篇）。

**切块策略**：

```
每篇 Markdown 按二级标题 ## 切分为若干 chunk
每个 chunk 保留：文件名（算法名）+ 章节标题 + 正文
chunk 大小上限：800 tokens（避免超出 context 窗口）
```

示例 chunk：

```
[来源：并查集.md § 内部原理]
为什么路径压缩有效：每次 find 都把沿途节点拉近根，下次再查询这些节点时
几乎 O(1) 完成。多次操作均摊下来非常快...
```

**向量化 + 存储**：

- 每个 chunk 调用 embedding API 得到向量（1536 维或 1024 维）
- 存储方案（选其一）：
  - **简单**：用 `numpy` 把向量存成 `.npy` 文件，检索时全量余弦相似度（80篇笔记切成约 400 chunk，全量计算 < 1ms，不需要专门向量数据库）
  - **扩展**：PostgreSQL + `pgvector` 扩展，`ALTER TABLE` 加向量列，支持 IVFFlat 索引

**推荐用简单方案**：项目规模不大，不必引入新的基础设施。

### 2.3 数据库设计

新增两张表：

```python
class KnowledgeChunk(models.Model):
    """切块后的笔记片段"""
    source_file = models.CharField(max_length=200)   # 来源文件路径
    algo        = models.ForeignKey(Algorithm, null=True, blank=True, on_delete=models.SET_NULL)
    section     = models.CharField(max_length=100)   # 章节标题
    content     = models.TextField()                  # 原文内容
    token_count = models.IntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

class ChunkEmbedding(models.Model):
    """向量（单独存，避免 chunk 表过重）"""
    chunk      = models.OneToOneField(KnowledgeChunk, on_delete=models.CASCADE)
    vector     = models.JSONField()   # 存 list[float]，简单方案
    model_name = models.CharField(max_length=50)  # 记录用了哪个 embedding 模型
```

### 2.4 Management Commands

```
python manage.py build_chunks    # 解析所有 md 文件，写入 KnowledgeChunk
python manage.py build_embeddings # 对所有 chunk 调 embedding API，写入 ChunkEmbedding
```

`build_embeddings` 支持断点续跑（跳过已有 embedding 的 chunk）。

### 2.5 API 端点

```
POST /api/ai/ask/
```

请求体：

```json
{
  "question": "并查集的路径压缩为什么有效？",
  "algo_id": "union-find"   // 可选，有则优先检索该算法的 chunk
}
```

处理流程（`judge/api_views.py`）：

```python
def post(self, request):
    q = request.data['question']
    algo_id = request.data.get('algo_id')

    # 1. 把问题向量化
    q_vec = embed(q)

    # 2. 检索 top-5 相关 chunk
    chunks = retrieve(q_vec, algo_id=algo_id, top_k=5)

    # 3. 拼 prompt
    context = '\n\n---\n\n'.join(c.content for c in chunks)
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user',   'content': f"参考资料：\n{context}\n\n问题：{q}"},
    ]

    # 4. 调用 LLM，流式返回（SSE）
    return StreamingHttpResponse(stream_claude(messages), content_type='text/event-stream')
```

`SYSTEM_PROMPT`：

```
你是一个算法竞赛学习助手，专注于帮助用户理解算法和数据结构。
请基于提供的参考资料回答问题，回答要简洁清晰，面向初学者。
如果参考资料中没有相关内容，请如实说明，不要编造。
代码示例优先用 C++。
```

### 2.6 前端实现

**入口 1：算法详情页右下角悬浮按钮**

`LearnDetailView.vue` 右下角加一个"问 AI"按钮，点击展开侧边抽屉（drawer），预填当前算法名作为上下文：

```
┌──────────────────────────────────────┐
│ 💬 问 AI                          ✕ │
│                                      │
│ 你正在学习：Dijkstra 算法             │
│                                      │
│ ┌──────────────────────────────────┐ │
│ │ Dijkstra 和 SPFA 有什么区别？    │ │
│ └──────────────────────────────────┘ │
│                                      │
│ [AI 回答逐字打印...]                  │
│                                      │
│ [输入框]                    [发送]   │
└──────────────────────────────────────┘
```

**入口 2：知识图谱页右上角全局搜索**

不限定算法，自由提问任何算法问题。

**流式显示**：复用现有 `JudgeResult.vue` 的逐字打印动画（`setInterval` + 字符追加），或改用 `EventSource` 接收 SSE 流。

---

## 实施顺序

| 阶段 | 内容 | 预估时间 |
|------|------|---------|
| **阶段 A** | 手写 `MANUAL_EDGES`，建 `AlgorithmEdge` 表，实现 `/api/algorithms/graph/`，前端 ECharts 图谱展示 | 3~4 天 |
| **阶段 B** | 解析 Obsidian 链接，`build_graph` 命令自动补边，图谱交互优化（筛选/点击跳转） | 2 天 |
| **阶段 C** | `build_chunks` + `build_embeddings` 命令，建知识库，实现检索逻辑 | 2~3 天 |
| **阶段 D** | `/api/ai/ask/` 端点 + SSE 流式输出，详情页"问 AI"抽屉 | 2~3 天 |
| **阶段 E** | 图谱页全局 AI 入口，历史对话记录（可选） | 1~2 天 |

**总计约 10~14 天**，可以并行开发阶段 A/B（纯后端不影响前端）和阶段 C（embedding 慢慢跑，不阻塞其他开发）。

---

## 技术选型说明

| 项目 | 选择 | 原因 |
|------|------|------|
| 图可视化 | ECharts Graph | 项目已引入，force layout 够用，不引入 D3.js |
| 向量存储 | numpy .npy（阶段一）| 80篇笔记 ~400 chunk，全量余弦搜索 <1ms，无需新基础设施 |
| Embedding 模型 | `text-embedding-3-small`（OpenAI）或 Claude 自带 | 维度低、价格便宜，后期可换 |
| LLM | Claude Sonnet（现有 API key） | 项目已有 AI 反馈功能，沿用现有调用链路 |
| 流式传输 | Django `StreamingHttpResponse` + SSE | 无需 WebSocket，简单可靠 |
