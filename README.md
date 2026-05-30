# ACM OJ — 算法竞赛在线评测平台

基于 **Django REST Framework + Vue 3** 的前后端分离算法竞赛 OJ 平台，支持代码自动评测、ICPC/IOI 赛制比赛、ECharts 数据可视化个人主页，并集成洛谷题目爬虫与 AI 代码评测反馈。

---

## 架构总览

```
浏览器
  └── Vue 3 SPA (frontend/)
        └── /api/* (axios + JWT 自动刷新)
              └── Django REST API
                    ├── MySQL
                    └── 评测引擎（后台线程异步执行，可选 Docker 沙箱）
```

| 目录 | 说明 |
|------|------|
| `acm_oj/` | Django 配置包（settings / urls） |
| `judge/` | 核心应用（模型 / API 视图 / 评测引擎 / 安全沙箱） |
| `frontend/` | Vue 3 SPA 前端（13 个页面） |

---

## 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 运行环境 |
| Django | 4.2 | Web 框架 |
| Django REST Framework | 3.15 | REST API |
| djangorestframework-simplejwt | **5.5.1** | JWT 认证（低版本在 Python 3.13 + setuptools ≥ 80 上崩溃） |
| django-cors-headers | 4.3 | 跨域支持（开发环境） |
| django-environ | 0.11 | 环境变量管理（`.env`） |
| MySQL | 8.0 | 主数据库（utf8mb4） |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.x | 前端框架（Composition API） |
| Vue Router | 4.x | 客户端路由（13 个页面） |
| Pinia | 2.x | 状态管理（JWT 持久化 + 提交轮询） |
| Vite | 8.x | 构建工具（含开发代理） |
| Axios | 1.x | HTTP 请求（含 token 自动刷新） |
| Monaco Editor | 0.55 | 代码编辑器（VS Code 同款） |
| ECharts + vue-echarts | 5.x / 8.x | 数据可视化（5 种图表） |
| marked | 18.x | Markdown 渲染（含图片自适应） |

---

## 功能列表

### 首页
- 粒子网络 Canvas 动态背景 + 浮动算法文字装饰（`O(n log n)`、`dp[i][j]` 等）
- 平台统计数字（题数 / 提交数 / 用户数），进入视口时触发数字滚动动画
- 近 30 天提交趋势柱状图 + 评测结果分布环形图（ECharts）
- 近期比赛列表（进行中 / 即将开始）
- 最新题目列表（含难度徽章、通过率）
- 快速导航卡片 + 全站实时评测流（彩色头像 + 实时状态）
- 特性介绍区：4 张卡片，Scroll Reveal 动画

### 题库
- 题目列表：分页、8 级难度筛选、标签点击筛选、关键词搜索
- 登录后显示每道题的做题状态（AC ✓ / 已尝试 / 未做）
- 题目详情：左栏题面（Markdown + KaTeX）+ 右栏 Monaco 编辑器，左右分栏布局
- 语言支持：C / C++17 / Java / Python，切换语言自动填充代码模板
- 题目内图片自适应（`max-width: 100%`，不溢出容器）

### 评测
- 异步提交：POST 立即返回 `submission_id`，前端每 2 秒轮询状态
- 评测结果：AC / WA / TLE / MLE / RE / CE / NT（无测试点），含耗时和内存
- **逐测试点结果**：跑完全部测试点，结果存入 `test_results` JSONField，评测详情页展示洛谷风格格子
- AC 判重：同一用户同一题目只计一次通过
- 比赛提交自动归属：仅在比赛进行中且用户已报名时计入
- AI 代码反馈：评测后异步调用 LLM 分析，结果逐字打印展示（不阻塞评测返回）
- 评测详情页：总览卡 + 测试点格子（按状态配色）+ 源代码展示

### 评测记录
- 独立的评测记录页面（`/submissions`）
- 我的记录 / 全站记录 Tab 切换
- 含用户彩色头像、题目链接、状态徽章、语言、耗时、时间

### 比赛
- ICPC / IOI 赛制，报名、题目列表（A/B/C 编号）、用户做题状态
- 卡片网格布局，含题目数量、时间区间、私有赛标识
- 按状态筛选：进行中 / 即将开始 / 已结束
- 实时排行榜：ICPC 按通过题数降序 + 罚时升序，进行中每 30 秒自动刷新，金银铜牌图标

### 讨论区
- 发帖（Markdown 编辑 + 实时预览）、回复、浏览量统计
- 帖子可关联题目；作者可删除自己的帖子和回复

### 个人主页（数据可视化）
- 用户信息卡：Rating、AC 题数、总提交、AC 率
- **AC 题目列表**：全部 AC 过的题目，绿色可点击 chip
- AC 日历热力图（ECharts，GitHub 风格，近一年）
- 提交语言分布环形图（ECharts）
- AC 题目难度分布柱状图（ECharts）
- 近期提交记录列表
- **比赛历史**：参赛记录，含赛制、得分、罚时

### 排行榜
- AC 数 / Rating 双维度榜单，前三名奖牌图标，点击跳转个人主页

### 用户账户
- JWT 认证，Token 过期自动静默刷新；退出登录服务端 Token 黑名单
- 个人资料编辑（bio / 头像颜色）；修改密码
- **互动登录页**：全屏左右分栏，左侧 4 个 SVG 卡通角色（橙色半圆、紫色矩形、黑色竖形、黄色圆角矩形），眼睛实时跟随鼠标转动；聚焦用户名时角色好奇探头、眼睛放大；聚焦密码框时全部闭眼遮挡；按住密码眼睛图标时橙色偷看、其余三个保持闭眼；登录成功时全体跳起并绽开笑容，失败时一起摇头沮丧；"记住我"勾选后将用户名持久化到 localStorage，下次自动预填

### 其他
- Django Admin 后台：题目 / 测试数据（StackedInline + 可视化）/ 比赛 / 用户管理
- 洛谷题目爬虫：批量导入，AI 生成测试点双解交叉验证，支持断点续爬

---

## 项目结构

```
acm_oj/
├── .env                            # 环境变量（不提交 git）
├── .env.example                    # 环境变量模板
├── .gitignore
├── manage.py
├── requirements.txt
│
├── acm_oj/                         # Django 配置包
│   ├── settings.py
│   └── urls.py                     # /api/ + SPA catch-all
│
├── judge/                          # 核心应用
│   ├── models.py                   # 10 张核心数据表
│   ├── serializers.py              # DRF 序列化器
│   ├── api_views.py                # REST API 视图（26 个端点）
│   ├── api_urls.py                 # API 路由
│   ├── admin.py                    # 增强后台（StackedInline / 批量操作）
│   │
│   ├── views/                      # Django 模板视图（已拆分）
│   │   ├── __init__.py             # re-export，外部零感知
│   │   ├── auth.py
│   │   ├── problem.py
│   │   ├── submission.py
│   │   ├── contest.py
│   │   ├── discussion.py
│   │   └── user.py
│   │
│   ├── services/                   # 业务服务层
│   │   ├── judger.py               # judge_submission（评测主函数）
│   │   ├── sandbox.py              # 执行隔离（Docker / 直接两种后端）
│   │   ├── ai_feedback.py          # LLM 调用 + 异步反馈
│   │   └── rating.py               # Rating 计算
│   │
│   └── management/commands/
│       └── crawl_luogu.py          # 洛谷爬虫
│
├── Dockerfile.sandbox              # 沙箱镜像（gcc / OpenJDK / python3）
│
└── frontend/                       # Vue 3 SPA
    ├── vite.config.js              # 开发代理 /api → 8000，生产 minify
    ├── src/
    │   ├── api/                    # axios 请求封装（7 个模块）
    │   │   └── index.js            # JWT 拦截器 + 自动刷新
    │   │
    │   ├── stores/
    │   │   ├── user.js             # 登录态 / token 持久化
    │   │   └── submission.js       # 提交轮询状态机
    │   │
    │   ├── views/                  # 13 个页面
    │   │   ├── HomeView.vue            ★ 粒子动画 + ECharts + 内容网格
    │   │   ├── ProblemListView.vue     难度/标签/关键词筛选
    │   │   ├── ProblemDetailView.vue   ★ Monaco + 异步提交 + AI 反馈
    │   │   ├── SubmissionsView.vue     评测记录列表
    │   │   ├── LoginView.vue           ★ 卡通角色互动登录页（SVG + 鼠标追踪眼睛）
    │   │   ├── RegisterView.vue        ★ 同款卡通角色注册页
    │   │   ├── ContestListView.vue     卡片网格布局
    │   │   ├── ContestDetailView.vue
    │   │   ├── ContestRankingView.vue  ★ ICPC 榜单，30s 自动刷新
    │   │   ├── LeaderboardView.vue
    │   │   ├── DiscussionListView.vue
    │   │   ├── DiscussionDetailView.vue
    │   │   ├── DiscussionCreateView.vue
    │   │   └── ProfileView.vue         ★ ECharts 三图 + AC 列表 + 比赛历史
    │   │
    │   ├── components/
    │   │   ├── CodeEditor.vue          # Monaco 封装
    │   │   ├── MarkdownRenderer.vue    # Markdown + 图片自适应
    │   │   ├── JudgeResult.vue         # 评测结果 + 打字机 AI 反馈
    │   │   ├── DifficultyBadge.vue
    │   │   ├── StatusBadge.vue
    │   │   ├── AcCalendarChart.vue     # AC 热力图（ECharts）
    │   │   ├── LanguageDistChart.vue   # 语言分布饼图
    │   │   └── DifficultyDistChart.vue # 难度分布柱状图
    │   │
    │   └── router/index.js            # 14 条路由
    │
    └── dist/                          # 生产构建产出（npm run build 后生成）
```

---

## API 端点

所有 API 均挂载于 `/api/`，使用 JWT Bearer Token 认证。

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register/` | 注册，返回 access + refresh token |
| POST | `/api/auth/login/` | 登录，返回 access + refresh token |
| POST | `/api/auth/refresh/` | 刷新 access token |
| GET  | `/api/auth/me/` | 获取当前用户信息 |
| PATCH | `/api/auth/me/` | 修改个人资料（bio / 头像颜色 / 邮箱） |
| POST | `/api/auth/password/` | 修改密码 |
| POST | `/api/auth/logout/` | 退出登录（服务端 Token 黑名单） |

### 题目

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/problems/` | 题目列表（keyword / difficulty / tag / page） |
| GET  | `/api/problems/<id>/` | 题目详情 |
| POST | `/api/problems/<id>/submit/` | 提交代码，立即返回 submission_id |

### 提交记录

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/submissions/` | 提交列表（all=1 全站 / problem_id / status / user_id 筛选） |
| GET  | `/api/submissions/<id>/` | 单条详情，含 code、test_results（前端轮询用） |

### 用户

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/users/<id>/` | 用户主页（基本信息 + 近期提交 + AC 题目列表 + 比赛历史） |
| GET  | `/api/users/<id>/stats/` | 图表数据（热力图 / 语言分布 / 难度分布） |

### 比赛

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/contests/` | 比赛列表（tab=all/running/upcoming/ended），含题目数量 |
| GET  | `/api/contests/<id>/` | 比赛详情 + 题目列表 |
| POST | `/api/contests/<id>/register/` | 报名比赛 |
| GET  | `/api/contests/<id>/rank/` | 实时榜单（ICPC 罚时计算） |

### 排行榜 / 讨论 / 统计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/rank/` | 全站排行榜（tab=ac/rating） |
| GET  | `/api/stats/` | 平台统计（题数/提交数/用户数/状态分布/30天趋势/近期比赛/最新题目/实时评测流） |
| GET  | `/api/discussions/` | 讨论列表 |
| POST | `/api/discussions/create/` | 发帖 |
| GET  | `/api/discussions/<id>/` | 帖子详情 + 回复 |
| DELETE | `/api/discussions/<id>/` | 删除帖子（仅作者） |
| POST | `/api/discussions/<id>/replies/` | 发回复 |
| DELETE | `/api/discussions/<id>/replies/<reply_id>/` | 删除回复（仅作者） |

---

## 快速开始

### 后端

**1. 创建虚拟环境并安装依赖**

```bash
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
SECRET_KEY=用 python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" 生成
DB_PASSWORD=你的MySQL密码

# 可选：留空则禁用 AI 反馈，不影响评测功能
LLM_API_KEY=你的API密钥
LLM_API_URL=https://...
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

构建完成后，Django 自动检测 `frontend/dist/` 并启用 SPA 模式——**一个端口同时服务前后端**：

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

| 模型 | 字段亮点 |
|------|---------|
| `UserProfile` | Rating / AC 数 / 头像颜色 / 角色 |
| `Tag` | 算法标签，多对多关联题目 |
| `Problem` | Markdown 题面 / 8 级难度 / 时间内存限制 / 通过率（注解计算） |
| `TestCase` | 输入 / 期望输出 / 是否样例 |
| `Submission` | 状态（AC/WA/TLE/MLE/RE/CE/NT）/ 耗时 / 内存 / AI 反馈 / **test_results（JSON）** |
| `Contest` | ICPC / IOI / 公开 / 密码赛 |
| `ContestProblem` | 比赛题目（A/B/C 编号） |
| `ContestParticipant` | 得分 / 罚时 |
| `Discussion` | Markdown 帖子，可关联题目 |
| `DiscussionReply` | 回复 |

### 难度等级（对应洛谷）

| 等级 | 颜色 |
|------|------|
| 入门 | 绿 |
| 普及- / 普及/提高- | 蓝 |
| 普及+/提高 | 浅紫 |
| 提高+/省选- | 黄 |
| 省选/NOI- | 橙 |
| NOI/NOI+/CTSC | 红 |
| 暂无评定 | 灰 |

---

## 评测引擎

评测核心位于 `judge/services/judger.py → judge_submission()`，提交后立即在后台守护线程中异步执行。

```
POST /api/problems/<id>/submit/
    ↓ 立即返回 { submission_id, status: "Pending" }
    ↓
  后台线程：Pending → Judging → 最终状态（AC/WA/TLE/MLE/RE/CE/NT）
    ↓
前端每 2 秒轮询 GET /api/submissions/<id>/
```

**执行流程：**

```
写入源文件 → 编译 → 遍历全部测试点（不提前终止）→ 汇总结果 → 写库 → AI 分析（异步）
```

**沙箱隔离（`judge/services/sandbox.py`）：**

| 模式 | 配置 | 适用场景 |
|------|------|---------|
| 直接执行（默认） | `USE_DOCKER_SANDBOX=False` | Windows 本地开发 |
| Docker 沙箱 | `USE_DOCKER_SANDBOX=True` | 生产部署 |

Docker 模式强制：无网络访问（`--network=none`）、硬内存上限（超限 OOM-kill → MLE）、单核、PID 数限制（防 fork bomb）、源码只读挂载。

| 语言 | 编译器 | 标准 |
|------|--------|------|
| C | `gcc` | `-O2` |
| C++ | `g++` | `C++17 -O2 -static-libgcc -static-libstdc++`（Windows 静态链接） |
| Java | `javac` / `java` | `-Xmx256m` |
| Python | `python` | 解释执行 |

**特殊状态 NT（无测试点）：** 题目无测试数据时返回 NT，不计 AC、不更新 Rating，AI 以建议模式异步运行。

---

## 洛谷题目爬虫

从洛谷批量导入题目，AI 自动生成测试数据（双解交叉验证），支持断点续爬。

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

**测试数据生成质量保证：** 先调用 LLM 生成主解 A，再生成采用不同算法的验证解 B，只有 A 和 B 对同一输入输出完全一致时才入库，大幅降低错误标准答案概率。

---

## AI 代码反馈

评测完成后异步调用 LLM 接口分析代码，结果在评测详情页逐字打印展示（不阻塞评测返回）。配置写在 `.env`，留空则静默禁用，不影响评测功能。

- **WA / RE / TLE**：分析可能原因，给出改进方向
- **AC**：评价算法思路，建议优化空间
- **无测试点（NT）**：以建议模式运行，不做裁决

---

## 管理后台

访问 `http://127.0.0.1:8000/admin/`。

| 模块 | 主要操作 |
|------|---------|
| 题目 | 创建 / 编辑，StackedInline 管理测试数据（多行等宽编辑器） |
| 比赛 | 创建比赛、添加题目（含编号）、管理参赛者 |
| 测试点 | 独立列表页，支持按题目搜索，一键批量删除 AI 生成测试点（保留样例） |
| 用户资料 | 修改角色 / Rating |
| 提交记录 | 查看提交代码（只读） |
| 讨论 | 删除违规内容 |
