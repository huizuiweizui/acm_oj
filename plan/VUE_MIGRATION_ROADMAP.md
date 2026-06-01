# ACM OJ Vue 化改造路线图

## 总体架构目标

```
现在：  浏览器 ←→ Django（模板渲染 + 业务逻辑 + 评测引擎）

目标：  浏览器 ←→ Vue 3 SPA ←→ Django REST API ←→ 评测引擎/数据库
```

**核心原则：评测引擎（`judge/views.py` 第 351 行的 `judge_submission`）绝对不动，只改外层接口。**

---

## 阶段总览

| 阶段 | 内容 | 预计时间 | 论文价值 |
|---|---|---|---|
| 第一阶段 | 后端 REST API 化 | 2~3 周 | 架构设计章节 |
| 第二阶段 | Vue 前端框架搭建 | 1 周 | 技术选型章节 |
| 第三阶段 | 核心页面组件化 | 3~4 周 | 系统实现章节 |
| 第四阶段 | 数据可视化 | 1~2 周 | 创新点章节 |
| 第五阶段 | 收尾与论文整理 | 1 周 | — |

**总计：8~11 周**

---

## 第一阶段：后端 REST API 化（2~3 周）

### ✅ 1.1 安装依赖

```bash
pip install djangorestframework==3.15.0
pip install djangorestframework-simplejwt==5.3.0
pip install django-cors-headers==4.3.1
```

修改 `acm_oj/settings.py`：

```python
INSTALLED_APPS = [
    ...
    'rest_framework',
    'corsheaders',
    'judge',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # 必须放最前面
    ...
]

# JWT 认证配置
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}

# 开发阶段允许 Vue 开发服务器跨域
CORS_ALLOWED_ORIGINS = ['http://localhost:5173']
```

---

### ✅ 1.2 修改 settings.py（已完成）

### ✅ 1.2 新建序列化器文件

新建 `judge/serializers.py`，负责把 Model 对象转为 JSON。

**需要写的序列化器（按优先级）：**

| 序列化器 | 用途 |
|---|---|
| `UserSerializer` | 用户基本信息（id, username, avatar_url, rating） |
| `ProblemListSerializer` | 题目列表（id, title, difficulty, ac_rate, tags） |
| `ProblemDetailSerializer` | 题目详情（+ description, sample_input/output） |
| `SubmissionSerializer` | 提交记录（status, language, time_used, ai_feedback） |
| `ContestSerializer` | 比赛信息 |
| `DiscussionSerializer` | 讨论帖 |
| `TagSerializer` | 标签 |

---

### ✅ 1.3 改写视图为 API ViewSet（全部完成：题目列表/详情、注册/登录/me、提交列表/详情/提交代码、用户主页）

新建 `judge/api_views.py`，把 `judge/views.py` 里的视图逐个改写。

**优先级顺序（从简单到难）：**

| 原视图函数 | 改为 API 端点 | 难度 |
|---|---|---|
| `problem_list()` | `GET /api/problems/` | 低 |
| `problem_detail()` | `GET /api/problems/<id>/` | 低 |
| `register_view()` | `POST /api/auth/register/` | 低 |
| `login_view()` | `POST /api/auth/login/` → 返回 JWT token | 低 |
| `submission_list()` | `GET /api/submissions/` | 低 |
| `submit_code()` | `POST /api/problems/<id>/submit/` | **中** |
| `contest_list/detail()` | `GET /api/contests/` | 低 |
| `leaderboard()` | `GET /api/rank/` | 低 |
| `discussion_*()` | `GET/POST /api/discussions/` | 低 |
| `profile_view()` | `GET /api/users/<id>/` | 低 |

**最难的是 `submit_code`**，评测是同步阻塞的，需要改成异步返回：

```
提交 → 立即返回 submission_id（状态 Pending）
         ↓
      后台线程评测（不改评测引擎本身）
         ↓
前端每 2 秒轮询 GET /api/submissions/<id>/ 直到状态不为 Pending
```

---

### ✅ 1.4 新建 API 路由（已完成）

### 1.4 新建 API 路由

新建 `judge/api_urls.py`，在 `acm_oj/urls.py` 里挂载：

```python
# acm_oj/urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('judge.api_urls')),      # 新增：API 路由
    path('', include('judge.urls')),              # 保留：原有路由（过渡期两套并存）
]
```

> **过渡期两套路由并存，改一个页面测一个，不影响未改的页面。**

---

### ✅ 第一阶段全部完成

已实现的 API 端点汇总：
- `POST /api/auth/register/` `POST /api/auth/login/` `POST /api/auth/refresh/` `GET /api/auth/me/`
- `GET /api/problems/` `GET /api/problems/<id>/` `POST /api/problems/<id>/submit/`
- `GET /api/submissions/` `GET /api/submissions/<id>/`
- `GET /api/users/<id>/`
- `GET /api/contests/` `GET /api/contests/<id>/` `POST /api/contests/<id>/register/`
- `GET /api/rank/`
- `GET /api/discussions/` `POST /api/discussions/create/` `GET /api/discussions/<id>/` `POST /api/discussions/<id>/replies/`

---

## 第二阶段：Vue 前端框架搭建（1 周）

### ✅ 2.1 初始化 Vue 项目

在项目根目录同级新建前端目录：

```bash
# 在 e:\MyCode\ 下执行
npm create vue@latest frontend
cd frontend
npm install
```

选项选择：

| 选项 | 选择 | 原因 |
|---|---|---|
| TypeScript | 否 | 减少学习成本 |
| Vue Router | 是 | 页面路由必须 |
| Pinia | 是 | 状态管理必须 |
| ESLint | 是 | 代码规范 |

---

### ✅ 2.2 安装核心依赖

```bash
npm install axios                    # HTTP 请求
npm install @vueuse/core             # Vue 组合式工具库
npm install @monaco-editor/vue3      # Monaco 编辑器 Vue 版
npm install marked katex             # Markdown + 数学公式（直接复用原逻辑）
npm install echarts vue-echarts      # 数据可视化（论文亮点）
```

---

### ✅ 2.3 目录结构规划（已建立）

```
frontend/src/
├── api/                    # 所有 axios 请求封装
│   ├── auth.js             # 登录/注册
│   ├── problems.js         # 题目相关
│   ├── submissions.js      # 提交相关
│   ├── contests.js         # 比赛相关
│   └── index.js            # axios 实例（含 JWT 拦截器）
├── stores/                 # Pinia 状态管理
│   ├── user.js             # 用户登录状态、token
│   └── submission.js       # 当前提交状态（轮询）
├── views/                  # 页面级组件（对应原来 18 个模板）
│   ├── HomeView.vue
│   ├── ProblemListView.vue
│   ├── ProblemDetailView.vue
│   ├── ContestListView.vue
│   └── ...
├── components/             # 复用组件
│   ├── CodeEditor.vue      # Monaco 编辑器封装
│   ├── MarkdownRenderer.vue
│   ├── DifficultyBadge.vue
│   ├── StatusBadge.vue
│   └── UserStatsChart.vue  # ECharts 数据可视化
└── router/index.js         # Vue Router 路由配置
```

---

## 第三阶段：核心页面组件化（3~4 周）

### ✅ Week 1：简单列表页（热身）

**目标：先跑通一个完整的前后端链路。**

**1. ProblemListView.vue**
- 对应原 `judge/templates/judge/problem_list.html`
- 功能：分页、难度筛选、标签筛选、关键词搜索
- 技术点：`axios.get('/api/problems/')` + `computed` 过滤 + Vue Router 查询参数

**✅ 2. LoginView.vue / RegisterView.vue**
- 登录后把 JWT token 存入 Pinia store + localStorage
- axios 拦截器自动在每次请求头加 `Authorization: Bearer <token>`

---

### ✅ Week 2：中等复杂度页面（ContestList/Detail、Leaderboard 完成）

**3. ContestListView.vue**
- 标签页（进行中 / 即将开始 / 已结束）用 Vue 响应式过滤，不刷页面

**✅ 4. DiscussionView.vue**
- Markdown 渲染复用原来的 marked.js 逻辑，封装成 `MarkdownRenderer.vue`

**5. LeaderboardView.vue**
- 相对简单，主要是表格渲染

---

### ✅ Week 3：核心难点页面

**6. ProblemDetailView.vue** ⭐ 最难

整个项目最复杂的页面，需要拆成子组件：

```
ProblemDetailView.vue
├── ProblemStatement.vue    # 题目描述（Markdown + KaTeX）
├── CodeEditor.vue          # Monaco 编辑器封装
├── SubmitPanel.vue         # 语言选择 + 提交按钮
└── JudgeResult.vue         # 评测结果展示（含 AI 反馈）
```

关键技术点：
- `@monaco-editor/vue3` 的 `v-model` 绑定代码内容
- 提交后启动轮询（`setInterval` + Pinia store 管理状态）
- AI 反馈的逐字展示效果（可选加分项）

**✅ 7. ContestRankingView.vue**
- 每 30 秒自动刷新（`onMounted` + `setInterval`）

---

### ✅ Week 4：个人主页（论文亮点）

**8. ProfileView.vue** ⭐ 数据科学专业亮点

拆成含数据可视化的子组件：

```
ProfileView.vue
├── UserInfoCard.vue         # 头像、rating、AC 数
├── AcCalendarChart.vue      # GitHub 风格 AC 热力图（ECharts）
├── LanguageDistChart.vue    # 提交语言分布饼图
├── DifficultyDistChart.vue  # AC 题目难度分布柱状图
└── RatingTrendChart.vue     # Rating 历史折线图
```

---

## ✅ 第四阶段：数据可视化（1~2 周）

这是数据科学专业背景最能体现的部分，也是论文创新点。

### ✅ 需要新增的 API 端点

在 `judge/api_views.py` 补充：

```python
# GET /api/users/<id>/stats/
# 返回：
{
  "ac_by_month": {"2024-01": 5, "2024-02": 8, ...},
  "ac_by_difficulty": {"简单": 20, "中等": 15, ...},
  "language_dist": {"C++": 60, "Python": 25, ...},
  "rating_history": [{"date": "...", "rating": 1200}, ...],
  "recent_ac": [{"problem_title": "...", "solved_at": "..."}, ...]
}
```

### 首页平台统计数据

```python
# GET /api/stats/
{
  "total_problems": 156,
  "total_submissions": 8420,
  "total_users": 342,
  "submissions_by_status": {"AC": 3200, "WA": 2100, ...},
  "daily_submissions": [{"date": "...", "count": 45}, ...]
}
```

---

## ✅ 第五阶段：收尾（1 周）

### ✅ 5.1 生产部署配置

```bash
# Vue 前端打包
cd frontend && npm run build
# 产出 dist/ 目录，可让 Django 托管，或用 Nginx 做反向代理
```

### 5.2 清理原有 Django 模板（可选）

改造完成后，`judge/templates/` 和 `judge/static/` 里的旧文件逐步删除（保留 Django Admin 用的部分）。

### ✅ 5.3 环境变量安全处理

`settings.py` 里的数据库密码和 AI API Key 已通过 `django-environ` 迁移至 `.env` 文件。`.env` 已加入 `.gitignore`，`.env.example` 作为模板提交。

---

## 论文章节对应关系

| 论文章节 | 对应阶段 | 核心内容 |
|---|---|---|
| 第2章 需求分析 | — | 功能模块、用例图 |
| 第3章 系统设计 | 第一阶段 | 前后端分离架构、REST API 设计、ER 图 |
| 第4章 技术选型 | 第二阶段 | Vue3 + DRF + JWT 选型理由对比 |
| 第5章 系统实现 | 第三阶段 | 各模块实现细节（重点写评测引擎 + Monaco 集成） |
| 第6章 数据分析与可视化 | 第四阶段 | **专业亮点**：用户行为分析、ECharts 图表设计 |
| 第7章 系统测试 | 第五阶段 | 功能测试、性能测试 |

---

## 建议的开始顺序

**第一天就能动手的三件事：**

1. 安装三个依赖包（djangorestframework、simplejwt、cors-headers）
2. 修改 `settings.py` 加入 DRF 和 CORS 配置
3. 新建 `judge/serializers.py`，先写 `ProblemListSerializer`，跑通 `/api/problems/` 这一个端点

> 先跑通一个端点的完整链路（序列化器 → API 视图 → URL → 浏览器看到 JSON），再扩展其余的，不要一次性全部改。
