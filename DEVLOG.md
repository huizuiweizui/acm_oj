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

## 阶段四：安全加固

### Fix 1 — Docker 沙箱（消除用户代码直接在主机执行的漏洞）

**问题**：`judge_submission()` 用 `subprocess.Popen` / `subprocess.run(shell=True)` 直接在主机上编译和运行用户提交的代码，恶意代码可任意访问主机文件系统和网络。

**方案**：新增 `judge/services/sandbox.py` 作为执行隔离抽象层，同时新增 `Dockerfile.sandbox`。

**新文件结构**：

```
judge/services/sandbox.py   # 执行隔离抽象（Docker / 直接两种后端）
Dockerfile.sandbox          # 沙箱镜像：gcc/g++/OpenJDK headless/python3
```

`sandbox.py` 对外只暴露三个函数：

```python
source_path(lang, tmp_dir)                              # 源文件路径（统一命名规范）
compile_code(lang, tmp_dir) -> (bool, str)              # 编译
run_code(lang, tmp_dir, input, timeout, memory_mb)      # 运行
  -> (returncode, stdout, stderr, timed_out)
```

Docker 模式（`USE_DOCKER_SANDBOX=True`）每测试点启动独立容器，强制：

```
--network=none          无网络访问
--memory=Xm             硬内存上限，超出 OOM-kill → exit 137 → MLE
--cpus=1                单核
--pids-limit=64         防 fork bomb
-v tmp_dir:/sandbox:ro  源码/二进制只读挂载
--tmpfs /tmp:exec,128m  JVM/Python 需要的可写 scratch（不落盘到宿主）
```

`judger.py` 同步改造：

- 编译 / 运行调用改为 `compile_code()` / `run_code()`
- 移除 Linux-only `/proc/<pid>/status` 内存监控线程（Docker 的 OOM-kill 替代）
- 新增 `returncode == 137` → `MLE` 判断

直接后端（`USE_DOCKER_SANDBOX=False`，默认）保留原有 subprocess 行为，供 Windows 本地开发。

构建命令：

```bash
docker build -f Dockerfile.sandbox -t acm-oj-sandbox:latest .
```

---

### Fix 2 — 无测试点默认 AC 漏洞

**问题**：题目无测试点时，系统让 AI 判定 AC/WA。AI 调用失败时兜底值是 `'AC'`，且判为 AC 后直接加 rating。题目刚发布、测试数据未上传时提交，几乎必得 AC 和 rating 提升。

**根因代码**（修复前）：

```python
verdict = first_line if first_line in ('AC', 'WA') else 'AC'  # AI 返回乱码时兜底 AC
verdict, ai_text = 'AC', ''                                    # AI 调用失败时兜底 AC
if verdict == 'AC':
    _update_rating(...)                                        # 直接加分
```

**修复**：无测试点时立即返回 `'NT'`（No Testcase），不计 AC、不更新 rating，AI 以建议模式异步运行。

```python
if not test_cases.exists():
    submission.status = 'NT'
    submission.save(update_fields=['status'])
    _async_ai_feedback(submission.id, problem.id)  # 给建议，不判裁决
    return {'status': 'NT', 'ai_feedback': ''}
```

**配套改动**：

- `judge/models.py`：`STATUS_CHOICES` 新增 `('NT', '无测试点')`
- `judge/migrations/0004_add_nt_status.py`：自动生成
- `frontend/src/components/StatusBadge.vue`：新增 `NT: { label: '无测试点', color: '#7f8c8d' }`，前端 polling 在收到 `'NT'` 时立即停止

---

### Fix 3 — 配置安全默认值硬化

**问题**：`settings.py` 在 `.env` 缺失时静默回落到不安全默认值：`DEBUG=True`、`ALLOWED_HOSTS=['*']`、`SECRET_KEY='django-insecure-...'`，部署到公网即为高危状态。

**修复**（`acm_oj/settings.py`）：

```python
# 修复前
env = environ.Env(
    DEBUG=(bool, True),
    ALLOWED_HOSTS=(list, ['*']),
    ...
)
SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-this-in-production')

# 修复后
env = environ.Env(
    DEBUG=(bool, False),      # 安全默认
    ALLOWED_HOSTS=(list, []), # 缺失时拒绝所有 Host
    ...
)
SECRET_KEY = env('SECRET_KEY')  # 无默认，缺失时启动即报 ImproperlyConfigured
```

`.env.example` 同步重写，标注必填项、两套环境（开发/生产）该填的值，以及 `SECRET_KEY` 生成命令：

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 当前状态

| 模块 | 状态 |
|------|------|
| Django 模板版 | 完整，已作为评测引擎底座保留 |
| REST API 层 | 完整（22 个端点） |
| Vue 3 SPA | 完整（12 个页面，3 个 ECharts 图表） |
| 评测引擎 | 已修复 time_used、memory_used，AI 异步化，Docker 沙箱，Windows 稳定性，逐测试点结果记录 |
| 测试点生成 | 双解交叉验证，大幅降低错误标准答案入库概率 |
| 自定义测试 | 独立 `/run/` 端点，不污染提交记录 |
| 比赛计分 | 已消除 N+1，横幅与实际逻辑一致，排行榜自动刷新 |
| Admin 后台 | 测试点可视化编辑，支持批量删除 AI 生成测试点 |
| 代码结构 | views.py 已拆分为 services/ + views/ |
| 安全 | Docker 沙箱、NT 状态、配置默认值硬化 |

## 待做（上生产前）

- [ ] 生产部署：`.env` 设 `DEBUG=False`、`ALLOWED_HOSTS=your-domain.com`、`USE_DOCKER_SANDBOX=True`，并 build 沙箱镜像
- [ ] `rejudge_nt` management command：管理员补充测试点后批量重判所有 `status='NT'` 的提交
- [ ] 切换内存测量为 cgroups v2 `memory.peak`（比 Docker OOM-kill 更精确，可获取峰值值而非只有 exit 137）
- [ ] 将 `_async_ai_feedback` 升级为 Celery 任务（需搭 Redis broker，比 daemon thread 更可靠）
- [ ] 测试数据批量生成工具（`judge/management/commands/gen_testcases.py` 已创建）
- [ ] 对历史 AI 生成测试点执行双解验证（Admin 批量删除后重跑 `crawl_luogu --update`）

---

## 阶段五：BUG 修复与评测稳定性

### Fix 1 — 比赛创建题目池 URL 路由冲突

**问题**：`acm_oj/urls.py` 先 include `judge.api_urls`（前缀 `api/`），再 include `judge.urls`。`judge/urls.py` 中注册的 `api/problems/` 被 DRF 的 `ProblemListAPIView`（需要 JWT）完全覆盖。浏览器访问时拿到 `{"detail": "..."}` 格式响应，前端 `data.problems` 为 `undefined`，JS 抛异常落入 `.catch()` 显示"网络异常，请稍后重试"，题目池显示 0 道题。

**修复**（`judge/urls.py`）：

```python
# 之前
path('api/problems/', views.api_problems, name='api_problems'),
# 之后（避开 DRF 的 api/problems/）
path('api/problem-pool/', views.api_problems, name='api_problems'),
```

URL name 不变，Django 模板 `{% url "api_problems" %}` 自动解析到新路径，无需改模板。

---

### Fix 2 — Django Admin 测试点管理增强

**问题**：原 `TestCaseInline` 使用 `TabularInline`，多行输入/输出挤在一行无法编辑。没有独立的测试点列表页，无法搜索某道题的所有测试点。

**改动**（`judge/admin.py`）：

- `TestCaseInline`：`TabularInline` → `StackedInline`，`formfield_overrides` 将 `TextField` 替换为 8 行等宽字体 `Textarea`，新增 `show_change_link = True`
- 独立注册 `TestCaseAdmin`：列表显示题目、排序、是否样例、输入/输出预览（截断 80 字符），支持按题目名/来源搜索，按 `is_sample` 筛选，`raw_id_fields = ['problem']` 防止大量题目时下拉卡顿
- 新增批量操作：**删除所选题目的 AI 生成测试点（保留样例）**，勾选某题全部测试点后一键清除 `is_sample=False` 的条目

---

### Fix 3 — LLM 测试点生成：单解 → 双解交叉验证

**根本问题**：`crawl_luogu.py` 的 `_generate_test_cases()` 用 LLM 写一个 Python 参考解，只在 1-2 个样例上验证，验证通过后让该解跑 AI 生成的输入来产生"标准答案"入库。参考解对样例通过不代表对边界情况正确，错误的标准答案导致正确提交判 WA。

**方案**：阶段一生成主解 A（原有流程），阶段二额外调一次 LLM 生成验证解 B（要求用**完全不同的算法**，禁止参考 A 的代码结构），同样在样例上验证，阶段三对每组 AI 输入同时执行 A 和 B，**只有两解输出完全一致时才入库**：

```
主解 A 通过样例
      ↓
验证解 B（不同算法）通过样例
      ↓
对每组 AI 输入: A(input) == B(input) → 入库
               A(input) != B(input) → 丢弃（两独立解同时出错概率极低）
```

退化机制：B 获取失败或样例不通过时，自动回退原来的单解模式，不中断爬虫主流程。

新增 `_build_verify_prompt()` 方法，在 prompt 中明确要求"禁止复用解 A 的代码结构，若 A 用 DP 则 B 用搜索/数学公式"。

不一致率 > 50% 时输出警告"该题参考解可能整体不可靠，建议人工复核"。

**相关改动**：
- `_run()` 闭包重构为通用 `_run_file(path, inp)` 函数
- `_validate_solution()` 重构为 `_validate_file(path)` 可复用
- 增加 `skipped_mismatch` 计数，汇总日志中打印丢弃比例

---

### Fix 4 — 自定义测试功能修复（端点错误 + 输入被忽略）

**问题**：测试按钮（"测试运行"）的 `data-url` 指向 `submit_code`，该视图完全忽略 `input` 字段，每次测试都对数据库存储的真实测试点做评测、写入一条 `Submission` 记录，用户填的自定义输入从未被使用。

**影响**：
1. 测试运行污染提交记录和统计数据
2. 处于比赛模式时，测试提交被错误关联到比赛，计入罚时
3. 自定义输入完全无效

**修复**：

新增 `custom_run` 视图（`judge/views/problem.py`）和 URL `problems/<id>/run/`：

```python
@login_required
@require_POST
def custom_run(request, problem_id):
    # 编译并运行用户代码（使用用户填写的 input），不保存 Submission 记录
    # 使用宽松的 10 秒超时，不与题目时间限制挂钩
```

模板 `data-url` 从 `{% url 'submit_code' problem.id %}` 改为 `{% url 'custom_run' problem.id %}`。

---

### Fix 5 — Windows 本地评测两个稳定性问题

**问题 A：进程启动开销导致 TLE 误判**

Windows 上启动 C++ 可执行文件有 200–500ms 系统开销，`_direct_run` 用 `timeout=time_limit_sec` 精确卡死，1 秒时间限制的题目（如 A+B Problem）必定超时，显示"运行超时，代码可能存在死循环"。

**修复**（`judge/services/sandbox.py`）：

```python
startup_buffer = 3.0 if sys.platform == 'win32' else 1.0
proc.communicate(input=input_data, timeout=timeout_sec + startup_buffer)
```

Docker 模式已有独立的 `+10s` 容器启动缓冲，此改动仅影响本地直接运行模式。

**问题 B：MinGW 编译产物运行崩溃（退出码 0xC0000005 ACCESS_VIOLATION）**

MinGW 动态链接的 C++ 可执行文件在子进程（无控制台、stdin/stdout 为 PIPE）中运行时，`libstdc++-6.dll` / `libgcc_s_seh-1.dll` CRT 初始化失败，退出码 3221225477（0xC0000005），没有 stderr 输出，显示"程序异常退出（退出码 3221225477）"。

**修复**：编译命令加 `-static-libgcc -static-libstdc++`，静态链接 C++ 运行时，消除 DLL 依赖：

```python
_static = '-static-libgcc -static-libstdc++' if sys.platform == 'win32' else ''
'C++': f'g++ -O2 -std=c++17 {_static} -o "{out}" "{src}"',
```

同时修正编译命令路径引号（防目录名含空格时 shell 解析失败），显式指定 `encoding='utf-8', errors='replace'`（避免中文 Windows GBK 编码误报），新增 exe 存在性检查并支持无 `.exe` 后缀的工具链回退：

```python
exe = os.path.join(tmp_dir, 'main.exe')
if not os.path.exists(exe):
    exe = os.path.join(tmp_dir, 'main')  # 兼容不自动加 .exe 的工具链
if not os.path.exists(exe):
    return -1, '', '找不到编译产物（main.exe / main），请确认 g++ 正常安装', False
```

---

### Fix 7 — 测试点逐条展示 + 提交跳转评测详情页

**需求**：
1. 题目页右侧"自定义测试"输入输出区域默认折叠，用户每次都要点击展开，体验差。
2. 提交后只在题目页内联显示一个总状态（AC / WA / …），无法看到哪个测试点过了、哪个没过，与洛谷"每个测试点一个绿/红格子"的体验差距明显。

#### 改动一：测试面板改为固定展开

**修改文件**：`problem_detail.html`、`problem_detail.css`、`problem_detail.js`

- `test-panel` div 默认加上 `expanded` class 和 `style="height:200px"`，体现"始终可见"语义
- CSS 将 `.test-panel .test-panel-body` 的 `display: none` 改为 `display: flex`，去掉 `.test-panel.expanded` 的分支，body 始终渲染
- JS 删除折叠/展开的 toggle click 监听器，移除"点击 header 切换 expanded class"逻辑；拖拽调整高度保留不变
- header 的 `cursor: pointer` 改为默认值，`:hover` 不再变色，视觉上不再暗示可点击

#### 改动二：每个测试点独立记录结果

**修改文件**：`judge/models.py`、`judge/services/judger.py`、`judge/migrations/0005_add_submission_test_results.py`

- `Submission` 新增 `test_results = JSONField(default=list)`，结构为列表，每条为 `{idx, status, time_ms}`
- `judge_submission()` 改为**跑完全部测试点**（原来遇到第一个非 AC 即提前返回），每点结果追加到 `case_results`
- `overall_status` 取第一个非 AC 的状态（保持传统 OJ 语义：WA 就是 WA，不混合）
- `submission.test_results = case_results` 随 `status` 等字段一起 `save()`
- CE 和 NT 时 `test_results = []`，不产生测试点格子

```python
for idx, tc in enumerate(test_cases, 1):
    ...
    case_results.append({'idx': idx, 'status': case_status, 'time_ms': elapsed_ms})
    if overall_status == 'AC' and case_status != 'AC':
        overall_status = case_status
# 全部跑完后统一保存
submission.test_results = case_results
submission.save(update_fields=['status', 'time_used', 'error_info', 'test_results'])
```

#### 改动三：提交后跳转评测详情页

**修改文件**：`problem_detail.html`、`problem_detail.js`

- 题目模板注入 `<script>var SUBMISSION_DETAIL_BASE = "{% url 'submission_detail' 0 %}";</script>`
- JS 提交成功回调改为：

```js
window.location.href = SUBMISSION_DETAIL_BASE.replace('/0/', '/' + data.submission_id + '/');
```

- 删除原有内联 result-panel（`result-section` div 及对应 CSS）

#### 改动四：评测详情页洛谷风格

**修改文件**：`judge/templates/judge/submission_detail.html`

全面重写，分三个卡片：

1. **总览**：R{id}、总状态 badge、用户、题目、语言、用时、内存、提交时间，grid 布局自适应
2. **测试点信息**：`tc-grid` flex 布局，每个点一张 `tc-card`（90px 宽），显示 `#idx`、状态文字、耗时；配色按状态区分：
   - AC → 绿色边框/背景
   - WA → 红色
   - TLE / MLE → 黄色
   - RE → 紫色
3. **源代码**：带最大高度滚动的等宽代码块

CE 时测试点卡片区域显示"编译错误，未运行任何测试点"。

---

### Fix 6 — 比赛模式横幅误导 + 排行榜不自动刷新

**问题 A：比赛模式横幅"提交将计入排行榜"与实际不符**

`problem_detail` 视图中 `contest_context = Contest.objects.filter(id=contest_id).first()`，不检查比赛是否已结束、用户是否已报名。横幅对所有人、所有状态都显示"当前提交将计入 a 的排行榜"。

而 `submit_code` 有严格检查：`Contest.objects.filter(id=..., start_time__lte=now, end_time__gte=now)` + `ContestParticipant.objects.filter(...).exists()`。两者不一致导致用户以为提交在计分，实际 `submission.contest = None`，排行榜没有任何变化。

**修复**（`judge/views/problem.py`）：

```python
is_active = c.start_time <= now <= c.end_time
is_registered = (request.user.is_authenticated
                 and ContestParticipant.objects.filter(contest=c, user=request.user).exists())
contest_context = c if (is_active and is_registered) else None
```

`contest_context` 现在只在"比赛进行中 + 当前用户已报名"时才设置，与 `submit_code` 的分配逻辑完全一致。

**问题 B：比赛排行榜无自动刷新**

比赛排行榜是 Django 模板静态渲染，提交后需手动刷新才能看到变化。

**修复**（`judge/views/contest.py` + `contest_ranking.html`）：

视图向模板传入 `contest_is_active` 布尔值。模板在比赛进行中时注入一段 JS，每 30 秒执行 `location.reload()`，右下角显示倒计时提示"比赛进行中，排行榜每 30 秒自动刷新（Xs）"。比赛结束后不再注入此脚本。
