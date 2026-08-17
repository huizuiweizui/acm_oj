## 阶段十：算法知识图谱 + AI 问答（RAG）

本阶段为毕业论文核心创新点之一，分三个阶段实现：图谱可视化（A）、Obsidian 链接解析补边（B）、RAG 知识库与流式问答（C）。

---

### Feature 1 — 算法知识图谱（阶段 A + B）

#### 数据模型：`AlgorithmEdge`

`judge/models.py` 新增关系边表：

```python
class AlgorithmEdge(models.Model):
    EDGE_TYPES = [
        ('prerequisite', '前置依赖'),   # A 是学习 B 的前置知识
        ('related',      '相关算法'),   # 同类、互为变种
        ('extends',      '扩展应用'),   # B 是 A 的进阶版
    ]
    source    = ForeignKey(Algorithm, related_name='out_edges', on_delete=CASCADE)
    target    = ForeignKey(Algorithm, related_name='in_edges',  on_delete=CASCADE)
    edge_type = CharField(max_length=20, choices=EDGE_TYPES, default='related')

    class Meta:
        unique_together = ['source', 'target']
```

迁移：`judge/migrations/0007_add_algorithm_edge.py`

#### 边数据来源一：手工关键依赖（`seed_edges`）

`judge/management/commands/seed_edges.py`：48 条精选关键边，涵盖所有高频学习路径依赖（如 `dijkstra → heap → prerequisite`、`aho-corasick → trie → extends`），`get_or_create` 幂等写入。

```bash
python manage.py seed_edges
# 完成: 新建 48 条，已存在跳过 0 条，缺失算法 0 处
```

#### 边数据来源二：Obsidian 链接自动解析（`build_graph`）

`judge/management/commands/build_graph.py`：

- 遍历 `algorithm/**/*.md`（共 106 个文件，跳过 `template/`、`锦囊/`）
- 正则定位"**前置知识**"章节（`^#{1,3}\s*前置知识`），章节内 `[[X]]` → `edge_type='prerequisite'`；正文其他位置 `[[X]]` → `edge_type='related'`
- 维护 `NOTE_TO_ALGO` 字典（80+ 条中文/英文笔记名 → `algo_id` 映射）
- 支持 `--dry-run`（只打印不写库）和 `--clear-auto`（清除自动边后重跑）

```bash
python manage.py build_graph
# 新建 157 条，已存在跳过 85 条，未匹配源文件 3 个（动态开点/平衡树/字符串模拟，无对应 algo_id，正常）
```

**最终边数据：205 条**（前置依赖 75 + 扩展应用 20 + 相关算法 110）

#### 图谱 API：`GET /api/algorithms/graph/`

`AlgorithmGraphAPIView`（`judge/api_views.py`）：

```json
{
  "nodes": [{ "id": "dijkstra", "name": "Dijkstra", "name_en": "...",
              "category": "图论", "difficulty": "进阶", "group": 5 }],
  "edges": [{ "source": "dijkstra", "target": "heap", "type": "prerequisite" }]
}
```

`group` 为 category 的数字编号，供前端按分类着色。URL 顺序：`graph/` 必须在 `<str:algo_id>/` 之前注册，避免路由覆盖。

#### 前端：`LearnGraphView.vue`（`/learn/graph`）

使用 ECharts `GraphChart`（项目已有 `vue-echarts 8.x`，无新依赖）：

**核心交互：**

| 功能 | 实现 |
|------|------|
| 力导向布局 | `layout: 'force'`，repulsion=340，edgeLength=[60,200]，layoutAnimation |
| 节点大小 | 由**入度+出度**决定，基础大小按难度（入门 14 / 提高 18 / 进阶 22），degree 每增 1 加 1px，最大 42 |
| 分类着色 | 9 个分类各有固定色，图例联动隐藏/显示对应节点 |
| 边类型区分 | 前置依赖（红实线） / 扩展应用（紫实线） / 相关算法（灰虚线） |
| 难度筛选 | 工具栏三个 Toggle 按钮，动态过滤可见节点和边 |
| 节点点击 | `router.push('/learn/:algo_id')` 跳转详情页 |
| Tooltip | 显示中英文名、分类、难度、可见连接数、跳转提示 |
| 重置视图 | 按钮调用 `chart.dispatchAction({ type: 'restore' })` |
| 统计 header | 实时显示 "N 个算法 · M 条关系" |

**主题适配（`MutationObserver`）：**

用 `MutationObserver` 监听 `<html data-theme="...">` 属性变化，`theme` 为派生 computed：

```js
const isDark = ref(...)
themeObserver = new MutationObserver(() => {
  isDark.value = document.documentElement.getAttribute('data-theme') !== 'light'
})
```

ECharts option 中所有颜色（节点标签 `labelColor`、tooltip 背景/文字/边框、图例文字、相关关系边颜色）均引用 `theme.value.*`，切换主题时 option 自动重算，图谱实时更新，无需刷新。

---

### Feature 2 — AI 问答 RAG（阶段 C）

#### 数据模型：`KnowledgeChunk` + `ChunkEmbedding`

```python
class KnowledgeChunk(models.Model):
    source_file = CharField(max_length=300)          # 来源 .md 文件相对路径
    algo        = ForeignKey(Algorithm, null=True)   # 关联算法（可为空）
    section     = CharField(max_length=200)          # 章节标题（## 标题）
    content     = TextField()                        # 原文内容
    token_count = IntegerField()                     # 估算 token 数（汉字×2 + ASCII×0.3）

class ChunkEmbedding(models.Model):
    chunk      = OneToOneField(KnowledgeChunk)
    vector     = JSONField()                         # list[float]，简单方案存 DB
    model_name = CharField(max_length=100)           # 记录使用的 embedding 模型
```

迁移：`judge/migrations/0008_add_rag_models.py`

#### 知识库构建：`build_chunks`

`judge/management/commands/build_chunks.py`：

- 遍历 99 个算法 `.md` 文件（跳过 template / 锦囊）
- 按 `## 二级标题` 切分为独立 chunk，首段作 `section='概述'`
- 超过 800 token 的 chunk 按空行二次拆分
- 支持 `--clear`（清空重建）和 `--dry-run`

```bash
python manage.py build_chunks
# 完成: 99 个文件 → 已写入 1149 个 chunk
```

#### 向量化：`build_embeddings`

`judge/management/commands/build_embeddings.py`：

- 依赖 `.env` 中 `EMBED_MODEL`（Ark/OpenAI 兼容 embedding 端点 ID）
- 自动推导 base URL（从 `LLM_API_URL` 去掉 `/chat/completions`）
- **断点续跑**：跳过已有 `ChunkEmbedding` 的 chunk，只处理 pending 部分
- 批量调用（默认 `--batch 32`），API 失败时 sleep 2s 并继续
- 支持 `--reset`（删除所有旧向量重新生成）

```bash
python manage.py build_embeddings
# 待处理 1149 个 chunk，batch=32，model=ep-xxxx
# 完成: 新建 1149 条，失败 0 条
```

`.env` 新增配置项：

```
EMBED_API_KEY=          # 留空时复用 LLM_API_KEY
EMBED_API_BASE=https://ark.cn-beijing.volces.com/api/v3
EMBED_MODEL=            # 填写 Ark embedding 端点 ID 后启用语义检索
```

#### 检索与问答：`judge/services/rag.py`

**`retrieve(query, algo_id=None, top_k=5)`：**

1. 调用 Embedding API 对查询向量化（`_embed_query`）
2. 加载所有 `ChunkEmbedding.vector`，组成 numpy 矩阵 `(N, D)`
3. 余弦相似度：`b_norm @ a_norm`，取 top-k 索引
4. 若指定 `algo_id`，优先在该算法的 chunk 中检索
5. **退化机制**：无 embedding 数据（`EMBED_MODEL` 未配置）时，自动回退到 Django ORM 关键词匹配（`content__icontains`），不报错

**`stream_answer(question, chunks)`：**

- 拼接 SYSTEM_PROMPT + 检索到的 chunk 原文 + 用户问题
- 调用 `LLM_API_URL`（`stream=True`），逐行解析 SSE 响应
- `yield f'data: {json.dumps({"text": token})}\n\n'.encode()`
- 最后 `yield b'data: [DONE]\n\n'`

SYSTEM_PROMPT：

```
你是一个算法竞赛学习助手，专注于帮助用户理解算法和数据结构。
请基于提供的参考资料回答问题，回答要简洁清晰，面向初学者。
如果参考资料中没有相关内容，请如实说明，不要编造。
代码示例优先用 C++。
```

#### 问答 API：`POST /api/ai/ask/`

`AskAIAPIView`（`judge/api_views.py`）：

```json
// 请求体
{ "question": "并查集的路径压缩为什么有效？", "algo_id": "union-find" }
```

返回 `StreamingHttpResponse`，`content_type='text/event-stream; charset=utf-8'`，每个 token 为一个 SSE 事件：

```
data: {"text": "路"}
data: {"text": "径"}
...
data: [DONE]
```

加 `X-Accel-Buffering: no`，防止 Nginx 缓冲导致流式响应卡顿。

#### 前端：`LearnDetailView.vue` 新增 AI 问答抽屉

**悬浮按钮（FAB）：**

```css
.ask-fab {
  position: fixed; right: 28px; bottom: 36px; z-index: 200;
  background: linear-gradient(135deg, #7c6af7, #22d3ee);
  box-shadow: 0 4px 20px rgba(124,106,247,0.4);
}
```

**侧边抽屉（Drawer）：**

- 点击 FAB 或 ESC 键打开/关闭，点击遮罩层关闭
- 头部显示当前算法名作为上下文（"正在学习：Dijkstra 算法"）
- Enter 发送，Shift+Enter 换行（`@keydown.enter` + `e.shiftKey` 判断）
- 使用 `fetch` + `ReadableStream` 逐块读取 SSE，`AbortController` 实现取消

---

### Fix — AI 问答改为多轮对话气泡界面

**问题**：初版抽屉只有单条问答（发送后只显示最新一条 AI 回复，无用户消息气泡，不像正常 AI 聊天界面）。

**改动（`LearnDetailView.vue`）：**

数据结构从单条 `answer` ref 改为消息列表：

```js
// 旧
const answer = ref('')

// 新
const messages = ref([])  // [{ role: 'user'|'ai', text: string, done: boolean }]
```

**发送流程：**

1. 用户点发送 → 立即 `messages.push({ role: 'user', text: q })` + 清空输入框
2. 再 `messages.push({ role: 'ai', text: '', done: false })` 创建 AI 占位消息
3. SSE 流式 token 追加到 `aiMsg.text`，完成后 `aiMsg.done = true`
4. 每次追加后调 `scrollBottom()`（`bodyRef.scrollTop = bodyRef.scrollHeight`）

**气泡样式：**

| 角色 | 位置 | 样式 |
|------|------|------|
| 用户 | 右对齐 | 紫色渐变背景（`#7c6af7 → #5b52d4`），白字 |
| AI | 左对齐 | `var(--bg-input)` 背景，左侧 AI 渐变圆形头像 |

AI 气泡内容用 `MarkdownRenderer` 渲染，流式过程中 `done=false` 时末尾显示 `▋` 光标。

多轮对话中每次提问都追加新气泡，历史记录完整保留，体验与主流 AI 产品对齐。

**SSE 客户端解析：**

```js
const reader = res.body.getReader()
const decoder = new TextDecoder()
let buf = ''
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  buf += decoder.decode(value, { stream: true })
  const lines = buf.split('\n'); buf = lines.pop()  // 末尾不完整行留给下次
  for (const line of lines) {
    if (!line.startsWith('data:')) continue
    const data = line.slice(5).trim()
    if (data === '[DONE]') break
    answer.value += JSON.parse(data).text
  }
}
```

**抽屉入场/离场动画（`<Transition name="drawer">`）：**

遮罩 `opacity: 0→1`，抽屉面板 `translateX(100%→0)`，时长 250ms ease。

---

### Embedding 选型过程

最初计划使用火山引擎方舟的 embedding 端点，但实际遇到以下问题：

- 账户内现有端点 `ep-20260214163310-gt8r9` 为 DeepSeek 对话模型，调 `/v3/embeddings` 接口返回 500
- 找到的 `doubao-embedding-vision-251215` 是多模态嵌入模型，使用专有 API 路径，与 OpenAI 兼容接口不兼容
- 方舟控制台未开通纯文本向量模型

**最终选型：硅基流动（SiliconFlow）`BAAI/bge-m3`**

- 平台：[siliconflow.cn](https://siliconflow.cn)，注册即用，完全免费
- 模型：`BAAI/bge-m3`，向量维度 1024，对中文算法笔记效果优于 OpenAI `text-embedding-3-small`
- 接口：OpenAI 兼容，`base_url=https://api.siliconflow.cn/v1`，代码零改动

`.env` 最终配置：

```
EMBED_API_KEY=sk-...（硅基流动 API Key）
EMBED_API_BASE=https://api.siliconflow.cn/v1
EMBED_MODEL=BAAI/bge-m3
```

### 向量生成结果

```bash
python manage.py build_embeddings --batch 20
# 待处理 1149 个 chunk，batch=20，model=BAAI/bge-m3
# ...
# 完成: 新建 1149 条，失败 0 条
```

### 语义检索验证

提问"Dijkstra 和 BFS 有什么区别"，top-3 召回：

```
[算法\3.搜索\2.BFS\0-1 BFS.md § 与相关算法的对比]  ← 精准命中对比章节
[算法\3.搜索\2.BFS\0-1 BFS.md § 核心思想]
[算法\7.图论\1.最短路\Dijkstra.md § 与相关算法的对比]
```

完全基于语义相似度，无任何关键词匹配，召回结果准确。

### 当前 RAG 状态（最终）

| 项目 | 状态 |
|------|------|
| 知识 chunk 数 | **1149 个**（99 个 md 文件） |
| 向量数 | **1149 个**（bge-m3，1024 维） |
| 检索模式 | **语义检索**（numpy 余弦相似度，全量 < 1ms） |
| 问答端点 | `POST /api/ai/ask/` SSE 流式返回 |
| 前端入口 | 算法详情页右下角渐变悬浮「问 AI」按钮 |

---
