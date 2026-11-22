# ACM OJ — 算法竞赛在线评测平台

基于 **Django REST Framework + Vue 3** 的前后端分离算法竞赛 OJ 平台，支持代码自动评测、ICPC/IOI 赛制比赛、ECharts 数据可视化个人主页，并集成算法知识图谱、RAG AI 问答与洛谷题目爬虫。

---

## 架构总览

```
浏览器
  └── Vue 3 SPA (frontend/)          14 个页面
        └── /api/* (axios + JWT 自动刷新)
              └── Django REST API    27 个端点
                    ├── MySQL
                    ├── 评测引擎（后台线程 / Docker 沙箱）
                    └── RAG 检索引擎（numpy 余弦相似度）
```

| 目录         | 说明                                            |
| ------------ | ----------------------------------------------- |
| `acm_oj/`    | Django 配置包（settings / urls）                |
| `judge/`     | 核心应用（模型 / API / 评测 / RAG / 图谱）      |
| `frontend/`  | Vue 3 SPA 前端（14 个页面）                     |
| `algorithm/` | 算法 Markdown 笔记（99 个文件，RAG 知识库来源） |

---

## 技术栈

### 前端

| 技术                  | 版本                          | 用途                                |
| --------------------- | ----------------------------- | ----------------------------------- |
| Node.js               | 20.x（≥20.19.0），或 ≥22.12.0 | 前端依赖安装、开发和构建            |
| Vue 3                 | 3.x                           | 前端框架（Composition API）         |
| Vue Router            | 4.x                           | 客户端路由（14 个页面）             |
| Pinia                 | 2.x                           | 状态管理（JWT 持久化 + 提交轮询）   |
| Vite                  | 8.x                           | 构建工具（含开发代理）              |
| Axios                 | 1.x                           | HTTP 请求（含 token 自动刷新）      |
| Monaco Editor         | 0.55                          | 代码编辑器（VS Code 同款）          |
| ECharts + vue-echarts | 5.x / 8.x                     | 数据可视化（图表 + 力导向知识图谱） |
| marked                | 18.x                          | Markdown 渲染                       |

### 后端

| 技术                          | 版本      | 用途                                                      |
| ----------------------------- | --------- | --------------------------------------------------------- |
| Python                        | 3.11+     | 运行环境                                                  |
| Django                        | 5.2 LTS   | Web 框架                                                  |
| Django REST Framework         | 3.16.x    | REST API                                                  |
| djangorestframework-simplejwt | **5.5.1** | JWT 认证（低版本在 Python 3.13 + setuptools ≥ 80 上崩溃） |
| django-cors-headers           | ≥4.7, <5.0 | 跨域支持                                                  |
| django-environ                | 0.13.0    | 环境变量管理（`.env`）                                    |
| MySQL                         | 8.0       | 主数据库（utf8mb4）                                       |
| openai                        | 2.x       | Embedding API 客户端（兼容硅基流动 / OpenAI）             |
| numpy                         | 2.x       | 向量余弦相似度检索                                        |

---

## 功能列表

### 首页

- 粒子网络 Canvas 动态背景 + 浮动算法文字装饰
- 平台统计数字，进入视口时触发滚动动画
- 近 30 天提交趋势柱状图 + 评测结果分布环形图（ECharts）
- 近期比赛列表、最新题目、快速导航、全站实时评测流

### 题库

- 题目列表：分页、8 级难度筛选、标签筛选、关键词搜索
- 登录后显示做题状态（AC ✓ / 已尝试 / 未做）
- 题目详情：左栏题面（Markdown）+ 右栏 Monaco 编辑器
- 语言支持：C / C++17 / Java / Python

### 评测

- 异步提交：POST 立即返回 `submission_id`，前端每 2 秒轮询
- 评测状态：AC / WA / TLE / MLE / RE / CE / NT（无测试点）
- **逐测试点结果**：全部测试点跑完，洛谷风格格子展示
- AI 代码反馈：评测后异步调用 LLM，结果逐字打印（不阻塞返回）

### 算法学习（`/learn`）

- 72 个算法卡片，支持分类筛选和关键词搜索
- 每个算法独立详情页（`/learn/:id`）：简介、步骤、复杂度表、三语言代码
- **AI 问答抽屉**：右下角渐变悬浮按钮，点击弹出侧边聊天界面
  - 多轮对话气泡界面（用户紫色气泡 / AI 灰色气泡 + 头像）
  - AI 回答基于 RAG 检索相关算法笔记，Markdown 格式渲染
  - SSE 流式逐字输出，实时滚动到最新消息

### 算法知识图谱（`/learn/graph`）

- **ECharts 力导向图**，展示算法节点及其关系
- 节点大小由连接度（degree）决定，9 个分类各自着色
- 边类型：前置依赖（红实线）/ 扩展应用（紫实线）/ 相关算法（灰虚线）
- 难度筛选（入门 / 提高 / 进阶），点击图例隐藏/显示分类
- 悬停 tooltip 显示算法名、分类、难度、连接数；点击节点跳转详情
- 主题适配：`MutationObserver` 监听主题切换，ECharts 颜色实时更新

### 比赛

- ICPC / IOI 赛制，卡片网格布局，按状态筛选
- 实时排行榜：按通过题数 + 罚时排序，进行中每 30 秒自动刷新

### 讨论区

- 发帖（Markdown）、回复、浏览量；作者可删除自己的内容

### 个人主页（数据可视化）

- AC 日历热力图 / 语言分布环形图 / 难度分布柱状图（ECharts）
- AC 题目列表、近期提交、比赛历史

### 排行榜

- AC 数 / Rating 双维度，前三名奖牌图标

### 用户账户

- JWT 认证，Token 自动刷新，退出登录服务端黑名单
- **互动登录页**：4 个 SVG 卡通角色，眼睛跟随鼠标，聚焦密码框闭眼，登录成功跳起
- 暗色 / 亮色主题切换（`localStorage` 持久化）

---

## 项目结构

```
acm_oj/
├── .env                            # 环境变量
├── .env.example                    # 环境变量模板
├── manage.py
├── requirements.txt
│
├── acm_oj/                         # Django 配置包
│   ├── settings.py
│   └── urls.py
│
├── algorithm/                      # 算法 Markdown 笔记（RAG 知识库来源）
│   ├── 算法/                        # 搜索、图论、DP、数论等
│   └── 数据结构/                     # 并查集、线段树、堆等
│
├── judge/                          # 核心应用
│   ├── models.py                   # 14 张数据表（含图谱 + RAG）
│   ├── serializers.py
│   ├── api_views.py                # REST API 视图（27 个端点）
│   ├── api_urls.py
│   ├── admin.py
│   │
│   ├── services/
│   │   ├── judger.py               # 评测主函数
│   │   ├── sandbox.py              # Docker / 直接两种执行后端
│   │   ├── ai_feedback.py          # LLM 异步代码反馈
│   │   ├── rating.py               # Rating 计算
│   │   └── rag.py                  # RAG 检索 + SSE 流式问答
│   │
│   └── management/commands/
│       ├── seed_algorithms.py      # 导入算法知识点
│       ├── seed_edges.py           # 写入 48 条手工关系边
│       ├── build_graph.py          # 解析 Obsidian [[链接]] 自动补边
│       ├── build_chunks.py         # 切分算法笔记为 1149 个 chunk
│       ├── build_embeddings.py     # 批量生成向量（支持断点续跑）
│       └── crawl_luogu.py          # 洛谷爬虫
│
├── Dockerfile.sandbox
│
└── frontend/
    ├── vite.config.js
    └── src/
        ├── views/                  # 14 个页面
        │   ├── HomeView.vue            粒子动画 + ECharts
        │   ├── ProblemListView.vue
        │   ├── ProblemDetailView.vue   Monaco + 异步提交 + AI 反馈
        │   ├── SubmissionsView.vue
        │   ├── LoginView.vue           卡通角色互动登录
        │   ├── RegisterView.vue
        │   ├── ContestListView.vue
        │   ├── ContestDetailView.vue
        │   ├── ContestRankingView.vue  ICPC 榜单，30s 刷新
        │   ├── LeaderboardView.vue
        │   ├── DiscussionListView.vue
        │   ├── DiscussionDetailView.vue
        │   ├── DiscussionCreateView.vue
        │   ├── LearnView.vue           算法卡片列表
        │   ├── LearnDetailView.vue     算法详情 + AI 问答抽屉
        │   ├── LearnGraphView.vue      ECharts 力导向知识图谱
        │   └── ProfileView.vue         ECharts 三图 + 数据可视化
        │
        └── components/
            ├── CodeEditor.vue
            ├── MarkdownRenderer.vue
            ├── JudgeResult.vue
            ├── AcCalendarChart.vue
            ├── LanguageDistChart.vue
            └── DifficultyDistChart.vue
```

---

## API 端点

所有 API 均挂载于 `/api/`，JWT Bearer Token 认证。

### 认证

| 方法        | 路径                  | 说明                 |
| ----------- | --------------------- | -------------------- |
| POST        | `/api/auth/register/` | 注册                 |
| POST        | `/api/auth/login/`    | 登录                 |
| POST        | `/api/auth/refresh/`  | 刷新 access token    |
| GET / PATCH | `/api/auth/me/`       | 获取 / 修改个人资料  |
| POST        | `/api/auth/password/` | 修改密码             |
| POST        | `/api/auth/logout/`   | 退出（Token 黑名单） |

### 题目 / 提交 / 用户 / 比赛

| 方法       | 路径                             | 说明                        |
| ---------- | -------------------------------- | --------------------------- |
| GET        | `/api/problems/`                 | 题目列表                    |
| GET / POST | `/api/problems/<id>/` `/submit/` | 详情 / 提交                 |
| GET        | `/api/submissions/`              | 提交列表                    |
| GET        | `/api/submissions/<id>/`         | 单条详情（含 test_results） |
| GET        | `/api/users/<id>/`               | 用户主页                    |
| GET        | `/api/users/<id>/stats/`         | 图表数据                    |
| GET        | `/api/contests/`                 | 比赛列表                    |
| GET        | `/api/contests/<id>/`            | 比赛详情                    |
| POST       | `/api/contests/<id>/register/`   | 报名                        |
| GET        | `/api/contests/<id>/rank/`       | 实时榜单                    |
| GET        | `/api/rank/`                     | 全站排行榜                  |
| GET        | `/api/stats/`                    | 平台统计                    |

### 讨论区

| 方法          | 路径                                            | 说明              |
| ------------- | ----------------------------------------------- | ----------------- |
| GET / POST    | `/api/discussions/` `/create/`                  | 列表 / 发帖       |
| GET / DELETE  | `/api/discussions/<id>/`                        | 详情 / 删除帖子   |
| POST / DELETE | `/api/discussions/<id>/replies/` `/<reply_id>/` | 发回复 / 删除回复 |

### 算法学习 + 知识图谱 + AI 问答

| 方法 | 路径                         | 说明                   |
| ---- | ---------------------------- | ---------------------- |
| GET  | `/api/algorithms/`           | 算法列表               |
| GET  | `/api/algorithms/graph/`     | 知识图谱节点 + 边数据  |
| GET  | `/api/algorithms/<algo_id>/` | 算法详情               |
| POST | `/api/ai/ask/`               | RAG 问答，SSE 流式返回 |

---

## 快速开始

以下命令从项目根目录执行。首次搭建时，先安装依赖并初始化数据库。已有本地环境时，可以直接看[本地启动](#本地启动)。

### 安装前端依赖

Node.js 支持 `20.19.0` 及以上的 20.x 版本，或 `22.12.0` 及以上的版本。推荐使用 Node.js 24。已有符合要求的版本时，可跳过 Node.js 安装。

**Windows（PowerShell）**

```bash
winget install nvm-windows --source winget
```

安装后重新打开 PowerShell，再执行下面两条命令。

```bash
nvm install 24
nvm use 24
```

**macOS / Linux（Bash 或 Zsh）**

```bash
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.7/install.sh | bash
. "$NVM_DIR/nvm.sh"
nvm install 24
nvm use 24
nvm alias default 24
```

**安装项目依赖**

```bash
node --version
npm --version
npm --prefix frontend ci
```

### 安装后端依赖

使用 Anaconda 创建 Python 3.12 环境。已创建 `acm_oj` 环境时，从激活环境开始。

```bash
conda create -n acm_oj python=3.12
conda activate acm_oj
python -m pip install -r requirements.txt
```

### 初始化数据库

首次搭建时，启动 MySQL，在 MySQL 客户端执行 `CREATE DATABASE acm_oj CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`。

在项目根目录将 `.env.example` 复制为 `.env`。如果已有 `.env`，直接编辑它。

**Windows（PowerShell）**

```bash
Copy-Item .env.example .env
```

**macOS / Linux**

```bash
cp .env.example .env
```

生成 Django 密钥，将结果填入 `.env` 的 `SECRET_KEY`，并填写 `DB_NAME`、`DB_USER`、`DB_PASSWORD`、`DB_HOST` 和 `DB_PORT`。

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

然后执行数据库迁移，创建本地管理员，并导入算法学习数据。

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_algorithms
python manage.py seed_edges
python manage.py build_graph
python manage.py build_chunks
```

已有管理员或已导入算法数据时，跳过对应的创建或导入命令。`build_chunks` 会追加知识片段，重复运行可能产生重复数据。

如果要使用向量检索，按[环境变量说明](#环境变量说明env)配置 Embedding 服务后再生成向量。基础功能可以先跳过这一步。

```bash
python manage.py build_embeddings
```

### 本地启动

打开两个终端，都从项目根目录开始。

**终端 1：Django 后端**

```bash
conda activate acm_oj
python manage.py check
python manage.py runserver 127.0.0.1:8000
```

**终端 2：Vue 前端**

```bash
npm --prefix frontend run dev
```

浏览器打开 [http://localhost:5173](http://localhost:5173)。Vite 会将 `/api/` 请求转发到 `http://127.0.0.1:8000`。也可以直接打开 [http://127.0.0.1:8000/api/stats/](http://127.0.0.1:8000/api/stats/) 检查后端是否返回 JSON。

已有数据库且希望补齐新版学习页的算法时，运行 `python manage.py seed_algorithms --missing-only`。这个选项只补充缺失的条目。

### 前端构建

从项目根目录执行构建，产物位于 `frontend/dist/`。

```bash
npm --prefix frontend run build
```

正式部署时，由 Web 服务器提供 `frontend/dist/` 中的资源，将前端页面路由回退到 `index.html`，并将 `/api/` 请求转发到运行 Django 的生产服务器。本地开发使用上面的双终端方式。

---

## 环境变量说明（`.env`）

```ini
SECRET_KEY=...            # Django 密钥（必填）
DEBUG=True
ALLOWED_HOSTS=*

DB_NAME=acm_oj
DB_USER=root
DB_PASSWORD=...           # 必填
DB_HOST=127.0.0.1
DB_PORT=3306

CORS_ORIGINS=http://localhost:5173

# AI 代码反馈（留空则禁用，不影响评测）
LLM_API_KEY=...
LLM_API_URL=https://...
LLM_MODEL=...

# RAG 向量检索（留空则退化为关键词匹配）
EMBED_API_KEY=...         # 留空时复用 LLM_API_KEY
EMBED_API_BASE=https://api.siliconflow.cn/v1
EMBED_MODEL=BAAI/bge-m3  # 推荐：硅基流动免费 bge-m3（1024 维，中文效果好）
```

---

## 数据模型

| 模型                                                | 说明                                                    |
| --------------------------------------------------- | ------------------------------------------------------- |
| `UserProfile`                                       | 用户扩展（Rating / AC 数 / 头像颜色）                   |
| `Problem`                                           | 题目（Markdown / 8 级难度 / 时间内存限制）              |
| `TestCase`                                          | 测试数据                                                |
| `Submission`                                        | 提交记录（含 `test_results` JSON 逐测试点结果）         |
| `Contest` / `ContestProblem` / `ContestParticipant` | 比赛系统                                                |
| `Discussion` / `DiscussionReply`                    | 讨论区                                                  |
| `Algorithm`                                         | 算法知识点、步骤、复杂度和示例代码                       |
| `AlgorithmEdge`                                     | 算法关系边（前置依赖 / 相关算法 / 扩展应用），共 205 条 |
| `KnowledgeChunk`                                    | 算法笔记切片（1149 个 chunk）                           |
| `ChunkEmbedding`                                    | Chunk 向量（bge-m3，1024 维）                           |

---

## 知识图谱数据来源

| 来源                               | 数量       | 说明                                              |
| ---------------------------------- | ---------- | ------------------------------------------------- |
| 手工维护（`seed_edges`）           | 48 条      | 关键学习路径依赖（Dijkstra→堆、Kruskal→并查集等） |
| Obsidian 链接解析（`build_graph`） | 157 条     | 解析 `algorithm/**/*.md` 中的 `[[前置知识]]` 章节 |
| **合计**                           | **205 条** | 前置依赖 75 + 扩展应用 20 + 相关算法 110          |

---

## 评测引擎

```
POST /submit/  → 立即返回 submission_id
    ↓
后台线程：Pending → Judging → AC/WA/TLE/MLE/RE/CE/NT
    ↓
前端每 2s 轮询 GET /api/submissions/<id>/
```

**沙箱模式：**

| 模式        | 配置                               | 场景             |
| ----------- | ---------------------------------- | ---------------- |
| 直接执行    | `USE_DOCKER_SANDBOX=False`（默认） | Windows 本地开发 |
| Docker 沙箱 | `USE_DOCKER_SANDBOX=True`          | 生产部署         |

Docker 模式：无网络、硬内存上限（OOM-kill → MLE）、单核、PID 限制、只读挂载。

---

## 洛谷爬虫

```bash
python manage.py crawl_luogu --count 100 --min-difficulty 1 --max-difficulty 2
python manage.py crawl_luogu --resume        # 断点续爬
python manage.py crawl_luogu --retry-failed  # 重跑失败题目
```

AI 生成测试数据采用**双解交叉验证**：主解 A + 独立验证解 B，两解输出一致才入库。

---

## 管理后台

访问 `http://127.0.0.1:8000/admin/`

| 模块     | 操作                                  |
| -------- | ------------------------------------- |
| 题目     | 创建 / 编辑，StackedInline 管理测试点 |
| 测试点   | 独立列表，一键批量删除 AI 生成测试点  |
| 比赛     | 创建，添加题目和参赛者                |
| 用户资料 | 修改角色 / Rating                     |
