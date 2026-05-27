# ACM OJ 开发日志

记录本项目从零到完整交付的所有阶段，包含架构决策、功能列表和代码层面的重要改动。

---

## 项目背景

毕业论文项目。目标是实现一个具备完整功能的算法竞赛 OJ 平台，技术亮点为数据可视化（ECharts 图表）和 AI 代码反馈。

- **作者**：计算机/数据科学方向在读生
- **论文创新点**：个人主页数据可视化（AC 热力图、难度分布、语言分布）

---

## 阶段一：Django 模板版（初版）

最初用 Django 传统 MVT 模式实现，全部页面由 Django 模板渲染。

**实现内容：**

- 10 张核心数据模型：`UserProfile`, `Tag`, `Problem`, `TestCase`, `Submission`, `Contest`, `ContestProblem`, `ContestParticipant`, `Discussion`, `DiscussionReply`
- 用户注册 / 登录 / 登出（Django 内置 auth）
- 题库：列表分页 + 难度/标签/关键词筛选 + 用户做题状态（AC / 已尝试 / 未做）
- 题目详情 + Monaco 代码编辑器
- 评测引擎：`judge_submission()` 子进程编译运行，支持 C / C++17 / Java / Python
- 提交记录列表 / 详情
- ICPC / IOI 双赛制比赛：报名、排行榜实时计算
- 讨论区：发帖 / 回复 / 浏览量
- 个人主页：近期提交、AC 题目标签分布
- 全站排行榜（AC 数 / Rating 双维度）
- 洛谷题目爬虫（批量导入，断点续爬，指数退避重试）
- Django Admin 后台

**评测引擎核心流程（初版）：**

```
写入源文件 → gcc/g++/javac 编译 → 逐测试点 subprocess.run() → 对比输出 → 写回结果
```

**AI 代码反馈（初版，同步阻塞）：**

- 评测完成后，同步调用 LLM API（timeout=30s），等待响应后才返回结果
- WA/RE/TLE 给出改进建议，AC 给出优化方向
- 无测试点时，由 AI 直接判定 AC/WA

---

## 阶段二：前后端分离重构（Vue 3 迁移）

将 Django 模板页面全部替换为 **Django REST Framework + Vue 3 SPA** 架构。这是项目最大的一次重构。

### Phase 1 — REST API 层（`judge/api_views.py`）

新建独立的 API 文件，不动原有 `views.py`，通过 `from .views import judge_submission` 懒导入评测引擎避免循环引用。

实现了 22 个 API 端点：

| 分类 | 端点数 | 说明 |
|------|--------|------|
| 认证 | 4 | 注册 / 登录 / 刷新 token / 获取当前用户 |
| 题目 | 3 | 列表 / 详情 / 提交代码 |
| 提交 | 2 | 列表 / 单条详情（轮询用） |
| 用户 | 2 | 主页信息 / 图表数据 |
| 比赛 | 4 | 列表 / 详情 / 报名 / 实时榜单 |
| 排行榜 | 1 | AC 数 / Rating 双维度 |
| 统计 | 1 | 平台汇总 + 30 天趋势 |
| 讨论 | 5 | 列表 / 发帖 / 详情 / 发回复 / 帖子管理 |

关键技术细节：

- JWT 认证：`djangorestframework-simplejwt 5.5.1`（必须 ≥ 5.5.1，低版本在 Python 3.13 + setuptools ≥ 80 上因 `pkg_resources` 被移除而崩溃）
- 异步评测：`SubmitCodeAPIView` 立即返回 `submission_id`，后台 `threading.Thread` 执行评测，前端轮询
- 比赛榜单 `GET /api/contests/<id>/rank/`：一次性取出所有提交记录，内存中计算排名，避免 N+1

### Phase 2 — Vue 项目初始化

```
frontend/
├── vite.config.js        # /api/* 代理到 8000，生产 minify
├── src/
│   ├── api/              # axios 请求封装（7 个模块）
│   │   └── index.js      # JWT 拦截器：401 时自动刷新 token，失败则跳登录
│   ├── stores/
│   │   ├── user.js       # 登录态 + token 持久化（localStorage）
│   │   └── submission.js # 提交轮询状态机
│   └── router/index.js   # 12 个路由，需要登录的路由添加 beforeEach 守卫
```

### Phase 3 — 所有业务页面

实现 12 个 Vue 页面：

| 页面 | 亮点 |
|------|------|
| `HomeView` | 平台统计 + ECharts 趋势图 + 状态分布环形图 |
| `ProblemListView` | 分页 + 多维筛选 + 做题状态标记 |
| `ProblemDetailView` | Monaco 编辑器 + 异步提交 + AI 反馈逐字打印动画 |
| `ContestRankingView` | ICPC 榜单，进行中每 30 秒自动刷新，金银铜牌图标 |
| `ProfileView` | ECharts 三图：AC 热力图（GitHub 风格）/ 语言饼图 / 难度柱状图 |
| `LeaderboardView` | AC 数 / Rating 双维度切换 |

**复用组件：**

- `CodeEditor.vue`：Monaco Editor 封装，切换语言自动填充模板
- `JudgeResult.vue`：评测结果展示 + AI 反馈逐字打印（`setInterval` 模拟打字机）
- `AcCalendarChart.vue`：ECharts heatmap（近一年 AC 日历）
- `LanguageDistChart.vue`：ECharts pie
- `DifficultyDistChart.vue`：ECharts bar

ECharts 踩坑：`XAxisComponent` / `YAxisComponent` 不从 `echarts/components` 导出，需用 `GridComponent` 代替。

Monaco Editor 踩坑：需在 `vite.config.js` 加 `optimizeDeps: { exclude: ['monaco-editor'] }` + blob stub worker，否则 Vite 预构建时崩溃。

### Phase 4 — 平台统计 API + 首页图表

新增 `GET /api/stats/`：

```json
{
  "total_problems": 200,
  "total_submissions": 1500,
  "total_users": 80,
  "status_dist": [{"status": "AC", "count": 600}, ...],
  "daily_submissions": [{"date": "2026-05-01", "count": 42}, ...]
}
```

HomeView 消费此接口，展示近 30 天提交趋势柱状图 + 评测结果分布环形图。

### Phase 5 — 生产环境配置

- **django-environ 迁移**：所有敏感配置（DB 密码、LLM 密钥、SECRET_KEY）迁移到 `.env`，提交 `.env.example` 模板
- **根目录 `.gitignore`**：排除 `.env`, `.venv`, `__pycache__`, `dist`, `node_modules`, 爬虫日志等
- **Vite 生产构建**：`npm run build` → `frontend/dist/`，Django `urls.py` 检测到 `dist/` 存在时自动启用 SPA catch-all，一个端口同时服务前后端

---

## 阶段三：评测引擎专项优化

在 Vue 迁移完成后，针对评测引擎的 5 个问题进行了专项修复和重构。

### Fix 1 — `time_used` 判断逻辑修正

**问题**：`if max_time` 是 truthiness 判断，当 `max_time = 0.0` 时误判为 0 保存。

**修复**（`judge/views.py:487`）：

```python
# 之前
submission.time_used = int(max_time * 1000) if max_time else 0
# 之后
submission.time_used = int(max_time * 1000) if max_time > 0 else 0
```

---

### Fix 2 — 内存测量（`memory_used` 字段首次生效）

**问题**：`memory_used` 字段存在但从未填写，MLE 状态永远不会触发。

**方案**：Linux 下使用 `/proc/<pid>/status` 的 `VmRSS` 字段轮询峰值（50ms 间隔），Windows 跳过（上 Docker 后自动生效）。

**关键改动**：

- `subprocess.run(shell=True)` → `subprocess.Popen(shell=False, 列表参数)`，拿到真正的程序 PID（而非 cmd.exe/sh 的 PID）
- 每个测试点启动一个 daemon 监控线程，读取 `/proc/<pid>/status`
- 每测试点结束后检查 `peak_mem > memory_limit * 1024 KB`，超限返回 `MLE`
- AC 时将 `max_memory_kb` 写入 `submission.memory_used`

```python
def _read_rss_kb(pid):
    try:
        with open(f'/proc/{pid}/status') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    return int(line.split()[1])
    except (OSError, ValueError):
        pass
    return 0
```

未来切换 cgroups v2 时可改为读 `/sys/fs/cgroup/memory.peak`（Docker 容器内无需 root，更精确）。

---

### Fix 3 — AI 反馈改为异步（不再阻塞评测返回）

**问题**：每次评测都同步等待 LLM 响应（timeout=30s），导致评测线程阻塞 30 秒，前端轮询看到的"Judging"状态持续异常长。

**方案**：新增 `_async_ai_feedback(submission_id, problem_id)` 辅助函数，verdict 写库后立即 return，AI 分析在 daemon 线程中异步完成。

```python
def _async_ai_feedback(submission_id, problem_id):
    def _worker():
        try:
            sub = Submission.objects.get(id=submission_id)
            prob = Problem.objects.get(id=problem_id)
            fb = _ai_call(_ai_suggest_prompt(sub, prob))
            if fb:
                sub.ai_feedback = fb
                sub.save(update_fields=['ai_feedback'])
        except Exception:
            pass
    threading.Thread(target=_worker, daemon=True).start()
```

6 处内联 `_ai_call`（CE / TLE / MLE / RE / WA / AC）全部替换为一行 `_async_ai_feedback(...)` 并立即返回 `'ai_feedback': ''`。

**特殊保留**：无测试点路径（AI 负责判定 AC/WA）仍为同步，因为 verdict 本身依赖 AI 结果。

前端无需改动，继续轮询 `/api/submissions/<id>/`，`ai_feedback` 从空字符串变为实际内容时自动展示。

---

### Fix 4 — 比赛罚时 N+1 查询优化

**问题**：`update_contest_score()` 每次 AC 提交都对该用户所有已 AC 题目全量重算罚时，AC 10 道题 = 20+ 条 SQL。

**根因**：

```python
# 旧版（伪代码）
for pid in all_ac_problems:      # N 次循环
    first_ac = query...          # 第 1 条 SQL
    wrong_count = query...       # 第 2 条 SQL
    penalty += ...
participant.save()
```

**新版（增量更新）**：

```python
def update_contest_score(submission):
    # 只判断当前提交是否为该题首次 AC
    first_ac = Submission.objects.filter(...).order_by('submitted_at').values('id').first()
    if not first_ac or first_ac['id'] != submission.id:
        return  # 非首次 AC，1 条 SQL 直接返回

    # 首次 AC：只算这道题的罚时增量
    ac_minutes = int(...)
    wrong_count = Submission.objects.filter(...).count()

    ContestParticipant.objects.filter(...).update(
        score=F('score') + 1,
        penalty=F('penalty') + ac_minutes + wrong_count * 20,
    )
```

| 场景 | 旧版 SQL 数 | 新版 SQL 数 |
|------|------------|------------|
| 非首次 AC | 2N+2 | **1** |
| 首次 AC | 2N+2 | **4** |

`F('score') + 1` 原子更新，顺带解决了并发重复计分问题。

---

### Fix 5 — `views.py` 拆分（1142 行 → 双层结构）

**问题**：`judge/views.py` 混合了视图函数、评测引擎、AI 调用、比赛分数、rating 更新，超过 1000 行，合并冲突困难。

**顺手修正**：`_DIFFICULTY_RATING` 字典的难度 key 使用了反斜杠（如 `'普及\提高-'`），与 `models.py` 中使用正斜杠的 `DIFFICULTY_CHOICES` 不一致导致排行榜 rating 计算全部失效——在迁移到 `services/rating.py` 时改正为正斜杠。

**新目录结构**：

```
judge/
├── services/
│   ├── ai_feedback.py   # _ai_call, _async_ai_feedback, prompt 构建, _LANG_CODE
│   ├── rating.py        # _DIFFICULTY_RATING（已修正 / 字符）, _update_rating
│   └── judger.py        # judge_submission, update_contest_score
└── views/               # 原 views.py 拆分为包
    ├── __init__.py      # re-export 所有名字（urls.py / api_views.py 零改动）
    ├── auth.py          # index, register_view, login_view, logout_view
    ├── problem.py       # problem_list/detail, submit_code, api_problems, learn
    ├── submission.py    # submission_list, submission_detail
    ├── contest.py       # contest_list/detail/register/ranking/create
    ├── discussion.py    # discussion_list/detail, create_discussion
    └── user.py          # leaderboard, profile_view, my_profile
```

`urls.py` 仍用 `from . import views`，`api_views.py` 仍用 `from .views import judge_submission`——两者都通过 `views/__init__.py` 的 re-export 透明工作，零改动。

---

## 当前状态

| 模块 | 状态 |
|------|------|
| Django 模板版 | 完整，已作为评测引擎底座保留 |
| REST API 层 | 完整（22 个端点） |
| Vue 3 SPA | 完整（12 个页面，3 个 ECharts 图表） |
| 评测引擎 | 已修复 time_used、memory_used，AI 异步化 |
| 比赛计分 | 已消除 N+1 |
| 代码结构 | views.py 已拆分为 services/ + views/ |

## 待做（上生产前）

- [ ] Docker 沙箱：隔离评测进程，防止恶意代码
- [ ] 切换内存测量为 cgroups v2 `memory.peak`（比轮询 `/proc` 更精确）
- [ ] 将 `_async_ai_feedback` 升级为 Celery 任务（需搭 Redis broker）
- [ ] 测试数据批量生成工具（`judge/management/commands/gen_testcases.py` 已创建）
