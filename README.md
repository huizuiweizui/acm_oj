# ACM OJ — 算法竞赛在线评测平台

基于 **Django REST Framework + Vue 3** 的前后端分离算法竞赛 OJ 平台，支持代码自动评测、ICPC/IOI 赛制比赛、数据可视化个人主页，并集成洛谷题目爬虫与 AI 代码评测反馈。

---

## 架构总览

```
浏览器
  └── Vue 3 SPA (frontend/)
        └── /api/* (axios + JWT 自动刷新)
              └── Django REST API
                    └── MySQL + 评测引擎（后台线程异步执行）
```

| 目录 | 说明 |
|------|------|
| `acm_oj/` | Django 配置包（settings / urls） |
| `judge/` | 核心应用（模型 / API 视图 / 评测引擎） |
| `frontend/` | Vue 3 SPA 前端 |

---

## 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 运行环境 |
| Django | 4.2 | Web 框架 |
| Django REST Framework | 3.15 | REST API |
| djangorestframework-simplejwt | 5.5.1 | JWT 认证 |
| django-cors-headers | 4.3 | 跨域支持（开发环境） |
| django-environ | 0.11 | 环境变量管理（`.env`） |
| MySQL | 8.0 | 主数据库（utf8mb4） |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.x | 前端框架（Composition API） |
| Vue Router | 4.x | 客户端路由（12 个页面） |
| Pinia | 2.x | 状态管理（JWT 持久化 + 提交轮询） |
| Vite | 8.x | 构建工具（含开发代理） |
| Axios | 1.x | HTTP 请求（含 token 自动刷新） |
| Monaco Editor | 0.55 | 代码编辑器（VS Code 同款） |
| ECharts + vue-echarts | 5.x / 8.x | 数据可视化（5 种图表） |
| marked | 18.x | Markdown 渲染 |

---

## 功能列表

### 首页
- 平台统计数字：总题数、总提交数、注册用户数
- 近 30 天提交趋势柱状图（ECharts）
- 评测结果分布环形图（ECharts）
- 功能导航卡片

### 题库
- 题目列表：分页、8 级难度筛选、标签点击筛选、关键词搜索
- 登录后显示每道题的做题状态（AC / 已尝试 / 未做）
- 题目详情：左栏题面（Markdown + KaTeX）+ 右栏 Monaco 编辑器，左右分栏布局
- 语言支持：C / C++17 / Java / Python，切换语言自动填充代码模板

### 评测
- 异步提交：POST 立即返回 `submission_id`，前端每 2 秒轮询状态
- 评测结果：AC / WA / TLE / MLE / RE / CE，含耗时和内存用量
- AC 判重：同一用户同一题目只计一次通过
- 比赛提交自动归属：自动检测当前活跃比赛
- AI 代码反馈：评测后调用 LLM 分析，结果逐字打印展示

### 比赛
- ICPC / IOI 赛制，报名、题目列表（A/B/C 编号）、用户做题状态
- 按状态筛选：进行中 / 即将开始 / 已结束
- 实时排行榜：ICPC 按通过题数降序 + 罚时升序，进行中每 30 秒自动刷新，金银铜牌图标

### 社区
- 讨论区发帖（Markdown 编辑 + 实时预览）、回复、浏览量统计
- 帖子可关联题目，支持按题目 ID 过滤

### 个人主页（数据可视化）
- 用户信息卡：Rating、AC 题数、总提交、AC 率
- AC 日历热力图（ECharts，GitHub 风格，近一年）
- 提交语言分布环形图（ECharts）
- AC 题目难度分布柱状图（ECharts）
- 近期提交记录列表

### 排行榜
- AC 数 / Rating 双维度榜单，前三名奖牌图标

### 其他
- JWT 认证，Token 过期自动静默刷新
- Django Admin 后台：题目 / 测试数据 / 比赛 / 用户管理
- 洛谷题目爬虫（批量导入，支持断点续爬）

---

## 项目结构

```
acm_oj/                             # 项目根目录
├── .env                            # 环境变量（不提交 git）
├── .env.example                    # 环境变量模板（提交 git）
├── .gitignore
├── manage.py
├── requirements.txt
│
├── acm_oj/                         # Django 配置包
│   ├── settings.py                 # 通过 django-environ 读取 .env
│   └── urls.py                     # /api/ + 旧模板路由 + SPA catch-all
│
├── judge/                          # 核心应用
│   ├── models.py                   # 10 张核心数据表
│   ├── serializers.py              # DRF 序列化器
│   ├── api_views.py                # REST API 视图（含比赛榜单 / 平台统计）
│   ├── api_urls.py                 # API 路由（22 个端点）
│   ├── views.py                    # 评测引擎（judge_submission）
│   ├── admin.py
│   └── management/commands/
│       └── crawl_luogu.py          # 洛谷爬虫
│
├── logs/                           # 爬虫日志
│
└── frontend/                       # Vue 3 SPA
    ├── vite.config.js              # 开发代理 /api → 8000，生产 minify
    ├── src/
    │   ├── api/                    # axios 请求封装
    │   │   ├── index.js            # axios 实例（JWT 拦截器 + 自动刷新）
    │   │   ├── auth.js
    │   │   ├── problems.js
    │   │   ├── submissions.js
    │   │   ├── contests.js
    │   │   ├── discussions.js
    │   │   └── users.js
    │   │
    │   ├── stores/                 # Pinia 状态
    │   │   ├── user.js             # 登录态 / token 持久化
    │   │   └── submission.js       # 提交轮询状态机
    │   │
    │   ├── views/                  # 12 个页面
    │   │   ├── HomeView.vue            ★ 平台统计 + ECharts
    │   │   ├── ProblemListView.vue
    │   │   ├── ProblemDetailView.vue   ★ Monaco + 异步提交 + AI 反馈
    │   │   ├── LoginView.vue
    │   │   ├── RegisterView.vue
    │   │   ├── ContestListView.vue
    │   │   ├── ContestDetailView.vue
    │   │   ├── ContestRankingView.vue  ★ ICPC 榜单，30s 自动刷新
    │   │   ├── LeaderboardView.vue
    │   │   ├── DiscussionListView.vue
    │   │   ├── DiscussionDetailView.vue
    │   │   ├── DiscussionCreateView.vue
    │   │   └── ProfileView.vue         ★ ECharts 数据可视化
    │   │
    │   ├── components/             # 复用组件
    │   │   ├── CodeEditor.vue          # Monaco 编辑器封装
    │   │   ├── MarkdownRenderer.vue    # Markdown 渲染
    │   │   ├── JudgeResult.vue         # 评测结果 + AI 反馈打字动画
    │   │   ├── DifficultyBadge.vue
    │   │   ├── StatusBadge.vue
    │   │   ├── AcCalendarChart.vue     # AC 热力图（ECharts）
    │   │   ├── LanguageDistChart.vue   # 语言分布饼图（ECharts）
    │   │   └── DifficultyDistChart.vue # 难度分布柱状图（ECharts）
    │   │
    │   └── router/index.js
    │
    └── dist/                       # 生产构建产出（npm run build 后生成）
```

---

## API 端点

所有 API 均挂载于 `/api/`，使用 JWT Bearer Token 认证。

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register/` | 注册，返回 access + refresh token |
| POST | `/api/auth/login/` | 登录，返回 access + refresh token |
| POST | `/api/auth/refresh/` | 刷新 token |
| GET  | `/api/auth/me/` | 获取当前用户信息 |

### 题目

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/problems/` | 题目列表（keyword / difficulty / tag / page） |
| GET  | `/api/problems/<id>/` | 题目详情 |
| POST | `/api/problems/<id>/submit/` | 提交代码，立即返回 submission_id |

### 提交记录

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/submissions/` | 提交列表（problem_id / status / user_id 筛选） |
| GET  | `/api/submissions/<id>/` | 单条详情（前端轮询评测状态用） |

### 用户

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/users/<id>/` | 用户主页（基本信息 + 近期提交） |
| GET  | `/api/users/<id>/stats/` | 图表数据（热力图 / 语言分布 / 难度分布） |

### 比赛

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/contests/` | 比赛列表（tab=all/running/upcoming/ended） |
| GET  | `/api/contests/<id>/` | 比赛详情 + 题目列表 |
| POST | `/api/contests/<id>/register/` | 报名比赛 |
| GET  | `/api/contests/<id>/rank/` | 实时榜单（ICPC 罚时计算） |

### 排行榜 / 讨论 / 统计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/rank/` | 全站排行榜（tab=ac/rating） |
| GET  | `/api/stats/` | 平台汇总（题数/提交数/用户数/状态分布/30天趋势） |
| GET  | `/api/discussions/` | 讨论列表 |
| POST | `/api/discussions/create/` | 发帖 |
| GET  | `/api/discussions/<id>/` | 帖子详情 + 回复 |
| POST | `/api/discussions/<id>/replies/` | 发回复 |

---

## 快速开始

### 后端

**1. 创建虚拟环境并安装依赖**

```bash
cd acm_oj
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

**2. 创建数据库**

```sql
CREATE DATABASE acm_oj CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**3. 配置环境变量**

```bash
cp .env.example .env
```

编辑 `.env`，至少填写：

```ini
DB_PASSWORD=你的MySQL密码

# 可选：留空则禁用 AI 反馈，不影响评测功能
LLM_API_KEY=你的API密钥
LLM_API_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
LLM_MODEL=你的模型endpoint
```

**4. 初始化并启动**

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### 前端（开发模式）

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173
```

> Vite 将 `/api/*` 自动代理到 `http://127.0.0.1:8000`，无需手动配置跨域。

### 前端（生产构建）

```bash
cd frontend
npm run build   # 产出 frontend/dist/
```

构建完成后，Django 自动检测 `frontend/dist/` 并启用 SPA 模式——一个端口同时服务前后端：

```
http://127.0.0.1:8000        → Vue SPA（所有页面）
http://127.0.0.1:8000/api/   → REST API
http://127.0.0.1:8000/admin/ → Django Admin
```

### 访问地址

| 地址 | 说明 |
|------|------|
| `http://localhost:5173` | Vue 前端（开发模式） |
| `http://127.0.0.1:8000` | 全栈（生产构建后） |
| `http://127.0.0.1:8000/admin/` | Django 管理后台 |

---

## 数据模型

| 模型 | 说明 |
|------|------|
| `UserProfile` | 用户扩展（Rating / AC 数 / 头像颜色 / 角色） |
| `Tag` | 算法标签 |
| `Problem` | 题目（Markdown 题面 / 8 级难度 / 时间内存限制） |
| `TestCase` | 测试数据（输入 / 期望输出） |
| `Submission` | 提交记录（状态 / 耗时 / 内存 / AI 反馈） |
| `Contest` | 比赛（ICPC / IOI / 公开 / 密码赛） |
| `ContestProblem` | 比赛题目关联（A/B/C 编号） |
| `ContestParticipant` | 参赛记录（得分 / 罚时） |
| `Discussion` | 讨论帖（Markdown / 关联题目） |
| `DiscussionReply` | 讨论回复 |

### 难度等级（对应洛谷）

| 等级 | 颜色 |
|------|------|
| 入门 | 绿 `#5cb85c` |
| 普及- / 普及/提高- | 蓝 `#2185d0` |
| 普及+/提高 | 浅紫 `#a0a0f0` |
| 提高+/省选- | 黄 `#ffcc00` |
| 省选/NOI- | 橙 `#ff8800` |
| NOI/NOI+/CTSC | 红 `#e03131` |
| 暂无评定 | 灰 `#888` |

---

## 评测引擎

评测函数位于 `judge/views.py → judge_submission()`，通过后台守护线程异步执行，不阻塞 API 响应。

```
POST /api/problems/<id>/submit/
    ↓ 立即返回 { submission_id, status: "Pending" }
    ↓
  后台线程：Pending → Judging → 最终状态（AC/WA/TLE/MLE/RE/CE）
    ↓
前端每 2 秒轮询 GET /api/submissions/<id>/，直到状态非 Pending/Judging
```

评测流程：

```
写入源文件 → 编译 → 逐测试点运行 → 对比输出 → 写回结果 → AI 分析（可选）
```

| 语言 | 编译器 | 标准 |
|------|--------|------|
| C | `gcc` | `-O2` |
| C++ | `g++` | `C++17 -O2` |
| Java | `javac` / `java` | `-Xmx256m` |
| Python | `python` | 解释执行 |

无测试数据时：自动调用 AI 评判代码正确性（返回 `AC` 或 `WA`）。

---

## 洛谷题目爬虫

从洛谷批量导入题目，支持断点续爬、失败重试。

**前置：配置 Cookie**

浏览器登录洛谷，从 DevTools → Network → Request Headers 找到 `_uid` 和 `__client_id`：

```powershell
$env:LUOGU_UID = "你的_uid"
$env:LUOGU_CLIENT_ID = "你的__client_id"
```

**常用命令**

```bash
# 100 道入门题
python manage.py crawl_luogu --count 100 --min-difficulty 1 --max-difficulty 2

# 综合题库
python manage.py crawl_luogu --count 500 --min-difficulty 2 --max-difficulty 6

# 断点续爬
python manage.py crawl_luogu --resume

# 重试失败题目
python manage.py crawl_luogu --retry-failed
```

| 选项 | 默认 | 说明 |
|------|------|------|
| `--count N` | 200 | 目标数量 |
| `--min-difficulty N` | 0 | 最低难度（0~7） |
| `--max-difficulty N` | 7 | 最高难度 |
| `--update` | 否 | 强制更新已有题目 |
| `--resume` | 否 | 从上次中断处继续 |
| `--retry-failed` | 否 | 只重跑失败题目 |

内置保护：随机请求间隔 1.5~3.5s、每 20 题额外休息、指数退避重试、进度自动持久化。

---

## AI 代码反馈

评测完成后自动调用 LLM 接口分析代码，结果在题目页逐字打印展示。配置写在 `.env`，留空则静默禁用，不影响评测功能。

- **WA / RE / TLE**：分析可能原因，给出改进方向
- **AC**：评价算法思路，建议优化空间
- **无测试点**：由 AI 直接判定 AC/WA 并给出理由

---

## 管理后台

访问 `http://127.0.0.1:8000/admin/`。

| 模块 | 主要操作 |
|------|---------|
| 题目 | 创建 / 编辑，内联管理测试数据 |
| 比赛 | 创建比赛、添加题目（含编号）、管理参赛者 |
| 用户资料 | 修改角色 / Rating |
| 提交记录 | 查看提交代码（只读） |
| 讨论 | 删除违规内容 |
