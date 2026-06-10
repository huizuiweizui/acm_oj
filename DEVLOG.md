# ACM OJ 开发日志

记录本项目从零到完整交付的所有阶段，包含架构决策、功能列表和代码层面的重要改动。

---

## 项目背景

毕业论文项目。目标是实现一个具备完整功能的算法竞赛 OJ 平台，技术亮点为数据可视化（ECharts 图表）和 AI 代码反馈。

- **作者**：数据科学方向在读生
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
| REST API 层 | 完整（27 个端点） |
| Vue 3 SPA | 完整（14 个页面，ECharts 图表 + 力导向知识图谱） |
| 评测引擎 | 已修复 time_used、memory_used，AI 异步化，Docker 沙箱，Windows 稳定性，逐测试点结果记录 |
| 测试点生成 | 双解交叉验证，大幅降低错误标准答案入库概率 |
| 自定义测试 | 独立 `/run/` 端点，不污染提交记录 |
| 比赛计分 | 已消除 N+1，横幅与实际逻辑一致，排行榜自动刷新 |
| Admin 后台 | 测试点可视化编辑，支持批量删除 AI 生成测试点 |
| 代码结构 | views.py 已拆分为 services/ + views/ |
| 安全 | Docker 沙箱、NT 状态、配置默认值硬化 |
| **算法知识图谱** | **ECharts 力导向图，62 节点 / 205 条边，分类着色，难度筛选，主题适配** |
| **AI 问答（RAG）** | **1149 chunk + 1149 向量（bge-m3）已入库，语义检索上线，SSE 流式问答** |

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

## 阶段六：REST API 人性化补全

针对已上线的 REST API 层补全了 5 个缺失功能，均在 `judge/api_views.py` 和 `judge/api_urls.py` 中实现。

### Fix 1 — 提交详情补全 `code` 与 `test_results` 字段

**问题**：`SubmissionSerializer` 未暴露 `code` 和 `test_results` 字段，`GET /api/submissions/<id>/` 拿不到源代码和逐测试点结果，用户无法复盘自己的提交。

**修复**（`judge/serializers.py`）：在 `SubmissionSerializer.Meta.fields` 中加入 `code`、`test_results`，并将 `test_results` 纳入 `read_only_fields`。

```python
fields = [
    'id', 'username', 'problem_id', 'problem_title',
    'language', 'status', 'time_used', 'memory_used',
    'error_info', 'ai_feedback', 'test_results', 'code', 'submitted_at',
]
```

---

### Fix 2 — 个人资料编辑接口（PATCH /api/auth/me/）

**问题**：`MeAPIView` 只有 GET，用户无法通过 API 修改 bio、头像颜色、邮箱等信息。

**修复**：为 `MeAPIView` 新增 `patch()` 方法，支持字段：`bio`、`avatar_color`、`avatar_url`（写入 `UserProfile`）、`email`（写入 Django `User`）。返回更新后的完整用户信息。

---

### Fix 3 — 修改密码接口（POST /api/auth/password/）

**新增** `ChangePasswordAPIView`，路由 `POST /api/auth/password/`。

接收 `old_password` 和 `new_password`，校验规则：

- 原密码正确
- 新密码 ≥ 6 位
- 新旧密码不能相同

---

### Fix 4 — 退出登录（POST /api/auth/logout/）+ Token 黑名单

**问题**：无退出登录接口，前端只能删 localStorage，服务端 refresh token 继续有效。

**修复**：

- `settings.py` 新增 `rest_framework_simplejwt.token_blacklist` 至 `INSTALLED_APPS`
- 执行 `python manage.py migrate` 生成 13 张黑名单相关表
- 新增 `LogoutAPIView`：接收 `refresh` token，调用 `RefreshToken(...).blacklist()` 使其服务端失效，无效 token 返回 400

```python
def post(self, request):
    try:
        RefreshToken(request.data.get('refresh')).blacklist()
    except TokenError:
        return Response({'detail': 'token 无效或已过期'}, status=400)
    return Response({'detail': '已退出登录'})
```

---

### Fix 5 — 删除讨论帖 / 回复

**问题**：讨论区发帖和回复后永久存在，无任何删除接口。

**修复**：

- `DiscussionDetailAPIView` 新增 `delete()` 方法，路由复用 `DELETE /api/discussions/<id>/`
- 新增 `DiscussionReplyDeleteAPIView`，路由 `DELETE /api/discussions/<id>/replies/<reply_id>/`

权限规则：只有帖子/回复的作者本人可以删除，他人操作返回 403。删除成功返回 204 No Content。

---

## 阶段七：Vue 前端旧模板样式还原

**背景**：Vue 3 SPA 重构完成后，旧 Django 模板中的大量设计细节（粒子动画、浮动算法文字、卡片布局、快速导航、实时评测流、AC 题目列表等"小巧思"）未被完整迁移，导致新前端观感远不如旧版。本阶段以旧模板为原版，逐页对齐。

### 后端扩展

**`GET /api/stats/` 新增三个字段**（`judge/api_views.py`）：

- `active_contests`：当前进行中 + 即将开始的比赛（最多 5 条），含状态标签
- `recent_problems`：最新发布的 5 道题，含动态计算的通过率
- `recent_submissions`：全站最近 8 条评测记录，含用户头像颜色

**`GET /api/users/<id>/` 新增两个字段**（`judge/api_views.py`）：

- `ac_problems`：该用户 AC 过的所有题目列表 `[{id, title}]`，按题目 ID 升序
- `contest_history`：参赛记录 `[{contest_id, contest_title, rule_type, score, penalty, date}]`

**`ContestSerializer` 新增 `problem_count` 字段**（`judge/serializers.py`）：
利用 `ContestListAPIView` 已有的 `.annotate(problem_count=Count('contest_problems'))` 注解，在序列化层直接暴露，前端无需额外请求。

---

### 前端改动

#### App.vue — 导航栏与页脚重构

- logo 从纯文字变为 `</>` 图标（JetBrains Mono 字体，紫色边框背景）+ `ACM OJ` 文字
- 新增"评测记录"导航链接，指向 `/submissions`
- 用户区域：纯用户名链接 → 彩色圆形头像（读取 `avatar_color`）+ 用户名组合
- 新增页脚：`ACM OJ 算法竞赛在线评测平台`

#### SubmissionsView.vue — 新建评测记录页

路由 `/submissions`。功能对齐旧模板 `submission_list.html`：

- 我的记录 / 全站记录 Tab 切换
- 提交 ID、用户、题目、结果徽章、语言、耗时、时间 7 列
- 用户头像（彩色圆形）+ 用户名可点击跳转个人主页
- 分页

#### HomeView.vue — 完整重写

旧版 `index.html` 全部设计还原到 Vue：

| 旧模板元素 | Vue 实现 |
|-----------|----------|
| Canvas 粒子网络背景 | `<canvas ref>` + `requestAnimationFrame` 粒子动画，主题色 `rgba(124,106,247)` |
| 浮动算法文字 | `.deco-line` 绝对定位，`@keyframes decoFloat` 上下浮动，显示 `O(n log n)`、`dp[i][j]` 等 |
| 眉头小圆点 + 副标题 | `.hero-eyebrow` + `.eyebrow-dot` 脉冲动画 |
| 统计数字滚动 | `IntersectionObserver` + `requestAnimationFrame` 三次方缓动，进入视口时触发 |
| 为什么选择 ACM OJ（4 张特性卡） | `.features-grid` 4 列，emoji 图标 + 标题 + 描述，hover 紫色边框 |
| 滚动显现动画 | `IntersectionObserver` 批量监听 `.reveal` 元素，入屏 → opacity+translateY 过渡 |
| 近期比赛列表 | 调 `/api/stats/` 取 `active_contests`，状态 Tag（绿/蓝） |
| 最新题目表格 | 调 `/api/stats/` 取 `recent_problems`，含难度徽章、通过率 |
| 快速导航 | 5 个导航项 + chevron 箭头 SVG，hover 高亮 |
| 实时评测流 | 调 `/api/stats/` 取 `recent_submissions`，彩色头像 + 用户名 + 题号 + 状态徽章 + 时间，绿色呼吸 live dot |

保留 Phase 4 的 ECharts 图表区（30 天提交趋势 + 评测结果分布），作为旧版没有的增强内容。

#### ProfileView.vue — 补充 AC 题目列表和比赛历史

- **AC 题目**：`GET /api/users/:id/` 返回 `ac_problems`，渲染为可点击绿色 chip，样式对齐旧版（绿色边框、背景，`rgba(34,197,94)` 色系）
- **比赛历史**：`GET /api/users/:id/` 返回 `contest_history`，渲染为行式列表，含赛制、得分、罚时、日期，点击跳转比赛详情

#### ContestListView.vue — 卡片网格布局

旧版 `contest_list.html` 样式完整迁移：

- 从竖向列表改为 `grid-template-columns: repeat(auto-fill, minmax(320px, 1fr))` 卡片网格
- 每张卡片：标题 + 状态 Tag（进行中绿/即将开始蓝/已结束灰）+ 题目数量（`编程题 × N`）+ 时间区间 + 锁图标（私有赛）
- 页头右侧"创建比赛"按钮（登录后可见），`+` 图标 SVG
- Tab 切换区改为胶囊风格（旧版样式）
- 两种空状态：全部空（🏟️ 暂无比赛）/ 筛选无结果（🔍 换个条件试试）

#### MarkdownRenderer.vue — 图片自适应

Markdown 渲染的题目描述中图片宽度溢出容器（洛谷导入的题目含行内坐标图）。

对齐旧版 `problem_detail.css` 的处理方式：

```css
.md-body img {
  max-width: 100% !important;
  width: auto !important;
  height: auto !important;
  display: block;
  border-radius: 6px;
}
```

---

## 阶段八：前端体验全面提升

本阶段集中完善前端体验，包含三个独立改动：登录 / 注册页卡通角色互动、暗色 / 亮色主题切换、算法学习页。

---

### Feature 1 — 登录 / 注册页卡通角色互动

**背景**：原登录页为暗色卡片表单，观感平淡，与整体风格也略有脱节。本阶段将登录 / 注册页重新设计为具有趣味交互的全屏角色动画页面。

### 整体布局

全屏左右分栏（无 navbar / footer）：

- **左侧**（52%）：浅灰背景（`#e8e8e8`），底部停靠 4 个 SVG 卡通角色
- **右侧**（48%）：纯白，极简下划线输入框表单，黑色登录按钮

`App.vue` 新增 `isAuthPage` computed（检测路由名是否为 `login` / `register`），在认证页隐藏 navbar 和 footer，主容器切换为 `.auth-content`（无内边距），使角色页面能铺满整个视口。

### 卡通角色（SVG inline）

4 个角色，全部在单张 `viewBox="0 0 420 320"` SVG 中用 `<g>` 分组绘制，底部对齐停靠：

| 角色 | 形状 | 配色 | 性格定位 |
|------|------|------|---------|
| 橙色半圆 | 半弧 + 扁平底边 | `#F97316` | 活泼开朗，常带笑容 |
| 紫色矩形 | 圆角矩形（底部更深） | `#7C3AED` | 略带傲娇，表情丰富 |
| 黑色竖形 | 细长矩形 | `#1a1a1a` | 冷静呆萌，圆眼睛 |
| 黄色圆角 | 胶囊形矩形 | `#FBBF24` | 温和内敛，嘴角平直 |

每个角色含：椭圆眼白 + 圆形瞳孔（可偏移）+ 嘴型路径（可切换 `smile / big-smile / sad / flat / sneak / o`）。

### 鼠标眼球追踪

```
onMouseMove → getSvgScreenPos(charCenter) → 计算角色到鼠标向量
→ eyeOffset.x/y = (dx/dist) × min(2.8, dist/50)
→ 绑定到各瞳孔 <circle :cx> :cy>
```

每帧实时更新，最大偏移 2.8px，距离越近偏移越小，产生自然"聚焦"感。

### 表情状态机

由 `focusState`（`none / email / password`）和 `loginState`（`idle / success / failure`）驱动 `expr` computed：

| 状态 | 橙色 | 紫/黑/黄 |
|------|------|---------|
| 聚焦用户名 | `eyeOpen: 1.3`，好奇探头 | 同样放大眼睛，向输入框倾斜 |
| 聚焦密码框 | `eyeOpen: 0`（闭眼） | `eyeOpen: 0`（集体遮挡） |
| 按住眼睛图标 | `eyeOpen: 1.2`（偷看） | 保持 `eyeOpen: 0`（遵守约定） |
| 登录成功 | `mouthType: big-smile` + bounce 动画 | 同上，全体弹跳 |
| 登录失败 | `mouthType: sad` + shake 动画 | 同上，全体摇头 |

CSS 动画：

```css
@keyframes bounce { 0%,100%{ translateY(0) }  30%{ translateY(-16px) }  60%{ translateY(-6px) } }
@keyframes shake  { 各帧 translateX ± 6px + rotate ± 3deg }
```

`<g>` 上绑定 `:class="{ bounce, shake }"` 和 `:transform`（body tilt），通过 `transition: transform 0.35s cubic-bezier(.34,1.56,.64,1)` 让姿态变化弹性过渡。

### 记住我

```
勾选 + 登录成功 → localStorage.setItem('remembered_user', username)
取消勾选 + 登录成功 → localStorage.removeItem('remembered_user')
页面加载时 → username.value = localStorage.getItem('remembered_user') || ''
              rememberMe.value = !!savedUsername
```

### Bug 修复记录

| 问题 | 原因 | 修复 |
|------|------|------|
| 页面切换跳闪 | `position: fixed; inset: 56px` 与 navbar sticky 冲突 | App.vue 隐藏 navbar/footer，改为 `height: 100vh` |
| 密码框不闭眼 | 旧逻辑：密码框聚焦时角色仍睁眼（改为"好奇探头"）| 重新定义：`inPw → eyeOpen: 0`，仅 peek 时橙色例外 |
| 记住我无效 | `rememberMe` 只是本地 ref，未连接任何存储 | 登录回调中读写 `localStorage` |

---

### Feature 2 — 暗色 / 亮色主题切换

**动机**：Vue SPA 使用硬编码暗色值（`#16162a`、`#1a1a2e` 等），无法响应用户的浅色偏好，且旧版 Django 模板已有完整亮色主题，需同步还原。

**实现方案**：

1. **CSS 变量层**（`frontend/src/assets/main.css`）：新增 `:root`（默认暗色）和 `[data-theme="light"]` 两套变量：

   | 变量 | 暗色值 | 亮色值 |
   |------|--------|--------|
   | `--bg-primary` | `#0f0f1e` | `#f2f2fb` |
   | `--bg-card` | `#16162a` | `#ffffff` |
   | `--border` | `#2d2d4e` | `#d8d8ee` |
   | `--text-primary` | `#e0e0f0` | `#1a1a2e` |
   | `--accent` | `#7c6af7` | `#6c5ae7` |
   | `--navbar-bg` | `#1a1a2e` | `#ffffff` |

2. **全局覆盖规则**（`main.css`）：用 `[data-theme="light"] .card`、`.table-wrap`、`.problem-table th` 等选择器覆盖各组件的硬编码暗色背景，无需逐一改组件文件。

3. **App.vue 逻辑**：
   - `isDark` ref，`onMounted` 时读取 `localStorage.getItem('theme')`（默认暗色）
   - `applyTheme(dark)` → `document.documentElement.setAttribute('data-theme', ...)`  + 写回 localStorage
   - `toggleTheme()` 切换并应用

4. **导航栏颜色变量化**（`App.vue scoped styles`）：将原来所有 `#1a1a2e`、`#c8c8d4`、`#3d3d5c` 等硬编码值全部替换为对应 CSS 变量，使导航栏在两种主题下都能正确渲染。

5. **切换按钮**：月亮 SVG（暗色时显示）/ 太阳 SVG（亮色时显示），置于导航栏用户区左侧。`v-if` 控制图标切换，transition 0.25s 过渡背景色。

---

### Feature 3 — 算法学习页（`/learn`）

对齐旧版 `learn.html` 全部设计，新建 `LearnView.vue`。

**页面结构：**

```
Hero（视差背景）
  ├── 六边形 SVG 网格（紫色 + 青色，opacity 0.07）
  ├── 浮动代码片段（O(n log n) / dp[i][j] / BFS/DFS 等，不同动画延迟）
  └── 渐变标题 + 副标题

吸附控制区（sticky top: 56px）
  ├── 搜索框（含搜索图标，focus 紫色边框）
  └── 分类标签栏（全部 / 基础算法 / 排序 / 搜索 / 贪心 / 动态规划 / 图论 / 数据结构 / 字符串 / 数学）

算法卡片网格（4 列，响应式）

详情视图（点击卡片切换，面包屑导航）
  ├── 算法简介段落
  ├── 执行步骤（渐变圆形序号列表）
  ├── 时空复杂度表
  └── 代码 Tab（C++ / Java / Python）
```

**数据层（纯前端，无 API）：**

`ALGORITHMS` 数组：62 个算法条目，字段 `{ id, name, nameEn, category, difficulty, desc }`

`DETAIL` 对象：目前收录有完整内容的算法（冒泡排序、二分查找、并查集），含 `description`、`steps[]`、`complexity[]`、`stable`、`codes { 'C++', Java, Python }`。其余算法点击后显示"整理中"占位页。

**卡片交互细节：**

- `::before` 伪元素：顶部 2px 紫→青渐变线，hover 时 `scaleX(0 → 1)`（从左展开）
- hover：`border-color: accent` + `translateY(-3px)` + `box-shadow`
- 难度徽章：入门（绿）/ 提高（黄）/ 进阶（红）三档配色

**视差效果：**

`onMounted` 监听 `window.scroll`，将 `.hero-parallax-bg` 的 `translateY` 设为 `scrollY * 0.3`，`onUnmounted` 清除监听，避免内存泄漏。

**导航栏新增"算法学习"链接**，路由 `/learn`，对应 `router/index.js` 第 15 条路由。

---

## 阶段九：算法学习页后端化 + 全量内容填充

**背景**：阶段八完成后，`LearnView.vue` 中算法数据全部硬编码在组件内（`ALGORITHMS` 数组 ~200 行，`DETAIL` 对象仅有 3 条有内容），维护困难，且详情页以内联切换（`detail.value` 切换）实现，URL 不变导致无法分享/书签/浏览器返回。本阶段将数据迁移至 Django 数据库并补全全部 62 个算法的详细内容。

### 架构变更

**旧架构：**

```
LearnView.vue 内硬编码 ALGORITHMS 数组（62条）+ DETAIL 对象（3条）
↓
点击卡片 → detail.value = {...} → 内联切换，URL 不变
```

**新架构：**

```
Django Algorithm 模型 → /api/algorithms/（列表）
                      → /api/algorithms/<algo_id>/（详情）
↓
LearnView.vue      — fetch 列表，点击卡片跳转到 /learn/:id
LearnDetailView.vue — fetch 单条详情，独立路由，URL 可分享
```

---

### Django 后端

#### 新增 `Algorithm` 模型（`judge/models.py`）

```python
class Algorithm(models.Model):
    algo_id     = CharField(max_length=50, unique=True)   # slug，如 'bubble-sort'
    name        = CharField(max_length=50)                 # 算法名称（中文）
    name_en     = CharField(max_length=100)                # 英文名
    category    = CharField(max_length=20)                 # 分类
    difficulty  = CharField(max_length=10)                 # 入门/提高/进阶
    desc        = CharField(max_length=300)                # 卡片简短描述
    description = TextField(blank=True)                    # 详情页长文介绍
    steps       = JSONField(default=list)                  # 执行步骤列表
    complexity  = JSONField(default=list)                  # 复杂度表 [{case,time,space}]
    stable      = BooleanField(null=True)                  # 是否稳定排序（None=不适用）
    codes       = JSONField(default=dict)                  # {'C++':..., 'Java':..., 'Python':...}
    sort_order  = IntegerField(default=0)
```

迁移文件：`judge/migrations/0006_algorithm.py`

#### 新增序列化器（`judge/serializers.py`）

- `AlgorithmListSerializer`：返回 `algo_id, name, name_en, category, difficulty, desc, sort_order`，用于卡片列表
- `AlgorithmDetailSerializer`：额外返回 `description, steps, complexity, stable, codes`，用于详情页

#### 新增 API 视图（`judge/api_views.py`）

- `AlgorithmListAPIView`：`GET /api/algorithms/`，`AllowAny`，`pagination_class=None`（全量返回，62 条）
- `AlgorithmDetailAPIView`：`GET /api/algorithms/<algo_id>/`，`AllowAny`，`lookup_field='algo_id'`

#### 新增路由（`judge/api_urls.py`）

```python
path('algorithms/',            AlgorithmListAPIView.as_view()),
path('algorithms/<str:algo_id>/', AlgorithmDetailAPIView.as_view()),
```

#### 数据导入命令（`judge/management/commands/seed_algorithms.py`）

Management command `python manage.py seed_algorithms`，使用 `update_or_create` 幂等导入，可重复执行。包含全部 62 个算法的完整数据，参考 `algorithm/` 目录下的 Markdown 笔记编写。

---

### Vue 前端

#### `LearnView.vue` 改造

- 删除硬编码的 `ALGORITHMS`（62 条）、`DETAIL`（3 条）、`CATEGORIES` 等静态数据，共约 400 行
- 删除内联详情视图模板（约 80 行 HTML + 200 行 CSS）
- `onMounted` 改为 `fetch('/api/algorithms/')` 拉取列表
- `openDetail(algo)` 改为 `router.push({ name: 'learn-detail', params: { id: algo.algo_id } })`
- 卡片字段名适配 API 返回格式：`nameEn → name_en`，`id → algo_id`

#### 新建 `LearnDetailView.vue`

新增独立详情页，路由 `/learn/:id`（`name: 'learn-detail'`）。

- `onMounted` → `fetch('/api/algorithms/${route.params.id}/')` 
- 加载中显示旋转 spinner；404 显示"找不到该算法" + 返回按钮
- 内容区块：面包屑 → 标题/英文名/难度/分类/练习按钮 → 简介 → 执行步骤 → 复杂度表 → 多语言代码 Tab
- 无内容时显示"整理中"占位（`description` 为空时触发）
- 样式与原 `LearnView` 内联详情完全一致，全部迁移至独立组件 `<style scoped>`

#### `router/index.js` 新增路由

```js
{ path: '/learn/:id', name: 'learn-detail', component: () => import('@/views/LearnDetailView.vue') }
```

---

### 算法内容填充

以 `algorithm/` 目录下的 Markdown 笔记为主要参考来源，补全全部 62 个算法的详细字段：

| 字段 | 说明 |
|------|------|
| `description` | 2~4 段深度介绍：核心思想、适用场景、关键细节、与相关算法对比 |
| `steps` | 5~7 条执行步骤，面向初学者，每步一句话 |
| `complexity` | 时空复杂度表（2~4 行），区分最好/平均/最坏情形 |
| `stable` | 排序算法标注稳定性，其他算法为 `null` |
| `codes` | C++ / Java / Python 三语言完整可运行代码，含注释 |

有对应 Markdown 笔记的算法直接从笔记提取（二分查找、DFS、BFS、并查集、Kruskal、Dijkstra、Floyd、拓扑排序、0-1背包、LCS、LIS、前缀和、差分、快速幂、位运算、线性筛、字典树、字符串哈希、KMP、单调栈、单调队列、线段树等），确保内容与笔记一致。

无对应笔记的算法根据算法知识独立撰写，风格保持统一。

**62 个算法全部完成**，`seed_algorithms` 执行结果：新增 62 条，更新 0 条（首次）。后续补充内容只需修改对应条目并重新运行 `seed_algorithms` 即可（`update_or_create` 保证幂等）。

---

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

## 阶段十一：算法详情页增强

本阶段对 `LearnDetailView.vue` 进行两项功能扩展，让详情页从"静态介绍卡"升级为完整的学习入口。

---

### Feature 1 — 学习路径推荐（利用知识图谱边数据）

**背景**：`AlgorithmEdge` 表中已有 205 条关系边，但详情页完全未利用这些数据，用户看不到"先学什么 / 学完学什么"。

#### 后端（`judge/serializers.py`）

`AlgorithmDetailSerializer` 新增三个 `SerializerMethodField`：

| 字段 | 含义 | 数据来源 |
|------|------|----------|
| `prerequisites` | 先学这些（当前算法的前置依赖） | `AlgorithmEdge(source=obj, edge_type='prerequisite').target` |
| `extends_to` | 学完继续（以当前算法为前置的算法） | `AlgorithmEdge(target=obj, edge_type__in=['prerequisite','extends']).source` |
| `related` | 相关算法（双向 related 边邻居，排除前两组） | `AlgorithmEdge` related 双向，去重后排除已在前两组中的节点 |

每个邻居节点返回 mini 格式：`{ algo_id, name, name_en, category, difficulty }`。

去重逻辑：`get_related` 先取 `prerequisites + extends_to` 的 `algo_id` 集合作为排除集，再筛 related 边，确保同一算法不出现在多个分组中。

#### 前端（`LearnDetailView.vue`）

在原有内容区（description / steps / codes）和 AI FAB 之间插入「学习路径」区块：

- **先学这些**（双左箭头图标）：红色 hover 边框卡片
- **学完继续**（双右箭头图标）：紫色 hover 边框卡片
- **相关算法**（横线图标）：accent 色 hover 边框卡片

每张卡片显示：算法名（大字）、英文名（monospace 小字）、分类标签、难度徽章，点击 `router.push('/learn/:algo_id')` 跳转。三组均为空时整个区块不渲染（`v-if`）。

**示例（Dijkstra 详情页）：**

```
先学这些：[BFS 入门] [堆 提高]
学完继续：[最小生成树 提高]
相关算法：[Floyd-Warshall 提高] [最短路 提高] [网络流 进阶] ...
```

#### Bug Fix — 同组件路由切换不刷新数据

**问题**：点击学习路径卡片从 `/learn/dijkstra` 跳到 `/learn/bfs` 时，Vue Router 复用同一组件实例，`onMounted` 不再触发，数据不更新，仍显示 dijkstra 的内容。

**修复**（`LearnDetailView.vue`）：

将加载逻辑提取为独立函数 `loadAlgo(id)`，同时在 `onMounted` 和 `watch(route.params.id)` 中调用：

```js
async function loadAlgo(id) { ... }

onMounted(() => loadAlgo(route.params.id))
watch(() => route.params.id, id => { if (id) loadAlgo(id) })
```

---

### Feature 2 — 算法笔记展示（KnowledgeChunk 渲染）

**背景**：`KnowledgeChunk` 表中已有 1149 个知识片段（从 99 个 Markdown 笔记按 `##` 标题切分），但详情页只展示 `Algorithm` 表中的简短字段（desc / steps / codes），笔记内容完全未对用户可见。

#### 后端（`judge/api_views.py` + `judge/api_urls.py`）

新增独立端点 `AlgorithmChunksAPIView`：

```
GET /api/algorithms/<algo_id>/chunks/
```

- 权限：`AllowAny`
- 返回：`[{ "section": "算法思路", "content": "..." }, ...]`，按写入顺序排列（`order_by('id')`）
- `algo_id` 不存在时返回 404

URL 注册时置于 `<algo_id>/` 之前，避免 Django 路由匹配歧义：

```python
path('algorithms/<str:algo_id>/chunks/', AlgorithmChunksAPIView.as_view()),
path('algorithms/<str:algo_id>/',        AlgorithmDetailAPIView.as_view()),
```

#### 前端（`LearnDetailView.vue`）

**并发加载**：`loadAlgo` 改为同时 `Promise.all` 请求算法详情和 chunks，不串行阻塞：

```js
const [algoRes, chunksRes] = await Promise.all([
  fetch(`/api/algorithms/${id}/`),
  fetch(`/api/algorithms/${id}/chunks/`),
])
```

**chunk 过滤**：展示前过滤掉：
- `section` 为 `前置知识`（已在学习路径区块展示）
- `section` 为 `全文`（整文 chunk，内容重复）
- `content` 有效长度 ≤ 30 字符（过短无意义的 chunk）

**展示逻辑**（插在已有详情内容之后、学习路径之前）：

```
算法笔记（section-hd 左侧紫色竖线）
  ├── [概述] → 无小标题，直接 MarkdownRenderer
  ├── [算法思路] → chunk-section-hd + MarkdownRenderer
  ├── [代码模板] → chunk-section-hd + MarkdownRenderer（含代码高亮）
  └── [复杂度分析] → chunk-section-hd + MarkdownRenderer
```

CSS 细节：
- `h1/h2` 在笔记区内隐藏（`display: none`），避免与页面结构重复
- `pre` 统一黑色背景（`#12121e`）+ `border-radius: 8px`
- `inline code` 使用 `var(--bg-input)` + 紫色字（`#a78bfa`）
- `blockquote` 左侧 3px accent 色竖线 + 背景色，对齐 Obsidian 笔记风格

**Dijkstra 详情页最终笔记 chunk 数：12 个，过滤后展示 10 个。**

---

## 阶段十二：知识图谱先修关系精标注

**背景**：阶段十完成知识图谱基础设施（`Algorithm` 表 ≡ 知识点，`AlgorithmEdge` 表 ≡ 关系边）后，`seed_edges.py` 中的 48 条手工边存在两个问题：

1. **语义错误**：若干边的 `edge_type` 不准确，与实际学习顺序不符：
   - `(dijkstra, shortest-path, 'extends')` → 应为 `prerequisite`（先学"最短路"概念，再学 Dijkstra 算法）
   - `(prefix-sum, difference-array, 'related')` → 应改为 `(difference-array, prefix-sum, 'prerequisite')`（前缀和是差分的前置知识）
   - `(bitmask-dp, dp-general, 'extends')` → 应为 `prerequisite`（DP 基础是状压 DP 的前置）
2. **覆盖不全**：排序子类对 `sort-general` 的依赖、图论算法对 `graph-general` 的依赖、数学工具链的依赖均未收录。

本阶段将 `seed_edges.py` 从 48 条扩展到 **76 条**精标注先修边，作为论文"知识图谱构建"一节的核心内容。

---

### 边类型语义定义

| 类型 | 含义 | 示例 |
|------|------|------|
| `prerequisite` | `target` 是学习 `source` 的前置知识，有严格学习顺序 | `(dijkstra, heap, prerequisite)` 意为：Dijkstra 需要先掌握堆 |
| `extends` | `source` 是 `target` 的进阶 / 具体实现，建立在 `target` 思路之上 | `(merge-sort, divide-conquer, extends)` 意为：归并排序是分治的典型应用 |
| `related` | 双向关联，同类问题或常配合使用，无严格先后顺序 | `(kmp, hashing, related)` 意为：两者都是字符串匹配的主流思路 |

---

### 先修边汇总（按分类）

#### 基础算法（7 条）

| 先学 → 后学 | 类型 | 理由 |
|------------|------|------|
| recursion → dfs | prerequisite | DFS 用递归实现 |
| recursion → divide-conquer | prerequisite | 分治用递归拆解子问题 |
| recursion → fast-pow | prerequisite | 快速幂递归版本 |
| recursion ↔ recurrence | related | 递推与递归互为对偶思维 |
| recurrence → dp-general | prerequisite | DP 本质是带记忆的递推 |
| recurrence ← fast-pow | extends | 快速幂基于 a^n=a^(n/2)² 递推关系 |
| two-pointers ↔ binary-search | related | 同属"索引缩减"类技巧 |

#### 排序（7 条）

| 先学 → 后学 | 类型 | 理由 |
|------------|------|------|
| sort-general → bubble-sort | extends | 冒泡是排序的具体实现 |
| sort-general → quick-sort | extends | 快速排序是排序的具体实现 |
| sort-general → merge-sort | extends | 归并排序是排序的具体实现 |
| sort-general → heap-sort | extends | 堆排序是排序的具体实现 |
| heap → heap-sort | prerequisite | 堆排序需要掌握堆结构 |
| divide-conquer → quick-sort | extends | 快速排序是分治的典型应用 |
| divide-conquer → merge-sort | extends | 归并排序是分治的典型应用 |

#### 搜索（7 条）

| 先学 → 后学 | 类型 | 理由 |
|------------|------|------|
| sort-general → binary-search | prerequisite | 二分要求序列有序 |
| graph-general → dfs | prerequisite | 图 DFS 需要图论基础 |
| graph-general → bfs | prerequisite | 图 BFS 需要图论基础 |
| queue → bfs | prerequisite | BFS 用队列维护层序 |
| search-general → dfs | extends | DFS 是深度优先搜索 |
| search-general → bfs | extends | BFS 是广度优先搜索 |
| search-general → binary-search | extends | 二分是有序空间的高效搜索 |

#### 贪心（2 条）

| 先学 → 后学 | 类型 | 理由 |
|------------|------|------|
| greedy → activity-select | extends | 活动选择是贪心的经典例题 |
| sort-general → activity-select | prerequisite | 活动选择先按截止时间排序 |

#### 动态规划（12 条）

| 先学 → 后学 | 类型 | 理由 |
|------------|------|------|
| dp-general → knapsack | extends | 背包是 DP 的经典模型 |
| dp-general → lcs | extends | LCS 是 DP 的经典模型 |
| dp-general → lis | extends | LIS 是 DP 的经典模型 |
| binary-search → lis | prerequisite | O(n log n) LIS 需要二分优化 |
| **dp-general → bitmask-dp** | **prerequisite** | **DP 是状压 DP 的基础** |
| bitwise → bitmask-dp | prerequisite | 状压 DP 用位运算枚举子集 |
| dp-general → interval-dp | extends | 区间 DP |
| dp-general → tree-dp | extends | 树形 DP |
| dfs → tree-dp | prerequisite | 树形 DP 用 DFS 遍历树 |
| dp-general → digit-dp | extends | 数位 DP |
| dp-general → floyd | extends | Floyd 是 DP 在图上的应用 |
| dp-general ↔ game-theory | related | 博弈论常用 DP 记忆化 |

#### 图论（18 条）

| 先学 → 后学 | 类型 | 理由 |
|------------|------|------|
| graph-general → shortest-path | prerequisite | 最短路需要图论基础 |
| **shortest-path → dijkstra** | **prerequisite** | **Dijkstra 是最短路的算法实现** |
| heap → dijkstra | prerequisite | 优先队列加速 Dijkstra |
| graph-general → dijkstra | prerequisite | |
| shortest-path → floyd | prerequisite | Floyd 是全源最短路算法 |
| graph-general → mst | prerequisite | |
| union-find → kruskal | prerequisite | Kruskal 用并查集合并连通分量 |
| mst → kruskal | extends | Kruskal 是 MST 的一种实现 |
| graph-general → kruskal | prerequisite | |
| graph-general → topo-sort | prerequisite | |
| bfs → topo-sort | prerequisite | Kahn 算法基于 BFS |
| graph-general → network-flow | extends | 网络流是图论的高级模型 |
| bfs → network-flow | prerequisite | Edmonds-Karp 增广路用 BFS |
| graph-general → bipartite | extends | |
| bfs → bipartite | prerequisite | 二分图染色用 BFS |
| network-flow ↔ bipartite | related | 二分图最大匹配 = 最大流特例 |
| dfs → lca | prerequisite | LCA 需要 DFS 遍历 |
| sparse-table → lca | prerequisite | 倍增 LCA 需要 Sparse Table |

#### 数据结构（8 条）

| 先学 → 后学 | 类型 | 理由 |
|------------|------|------|
| stack → monotone-stack | prerequisite | |
| queue → monotone-queue | prerequisite | |
| sort-general ↔ heap | related | 堆与排序强关联 |
| bitwise → bit | prerequisite | 树状数组依赖 lowbit 位运算 |
| divide-conquer → segment-tree | prerequisite | 线段树基于分治思想 |
| prefix-sum → sparse-table | extends | Sparse Table 是 RMQ 版前缀积 |
| hashing ↔ trie | related | 字典树与哈希同为字符串索引 |
| graph-general ↔ union-find | related | 并查集大量用于图连通性 |

#### 字符串（6 条）

| 先学 → 后学 | 类型 | 理由 |
|------------|------|------|
| brute-force → kmp | extends | KMP 是暴力匹配的线性优化 |
| hashing ↔ kmp | related | 两种字符串匹配的主流思路 |
| binary-search → suffix-array | prerequisite | 后缀数组上查询需要二分 |
| hashing ↔ suffix-array | related | 后缀数组与字符串哈希互补 |
| trie → aho-corasick | extends | AC 自动机在字典树上构建失配指针 |
| kmp → aho-corasick | extends | AC 自动机是 KMP 的多模式推广 |

#### 数学（9 条）

| 先学 → 后学 | 类型 | 理由 |
|------------|------|------|
| **prefix-sum → difference-array** | **prerequisite** | **差分数组用前缀和还原** |
| bitwise ↔ fast-pow | related | 快速幂常用位运算判奇偶 |
| fast-pow → matrix | prerequisite | 矩阵快速幂 |
| enumeration → sieve | extends | 线性筛是聪明的枚举优化 |
| fast-pow ↔ number-theory | related | 费马小定理用快速幂求逆元 |
| sieve → number-theory | prerequisite | 数论需要质数筛法 |
| fast-pow → combinatorics | prerequisite | C(n,r) mod p 需快速幂求阶乘逆元 |
| combinatorics → probability | prerequisite | 概率论建立在组合数基础上 |
| recurrence ↔ big-integer | related | 高精度按位逐步递推处理 |

---

### 运行命令

```bash
# --clear 先清空再写入，使修正后的 edge_type 生效
python manage.py seed_edges --clear
# 完成: 新建 76 条，已存在跳过 0 条，缺失算法 0 处

# 重新构建 Obsidian 链接自动解析的边（保留手工边）
python manage.py build_graph
# 新建 152 条，已存在跳过 90 条（手工边覆盖的部分），未匹配源文件 3 个（无 algo_id，正常）
```

---

### 最终图谱状态

| 指标 | 数值 |
|------|------|
| 知识节点（Algorithm） | **62 个** |
| 手工先修边（seed_edges） | **76 条** |
| 自动解析边（build_graph 净新增） | **152 条** |
| 总关系边 | **228 条** |
| prerequisite 边占比 | **~45%** |

---

## 阶段十三：三端教学平台（学生 / 教师 / 队长）

本阶段将系统从"单用户 OJ"升级为支持"学生 / 教师 / 管理员"三端分角色运营的教学平台，核心功能包括：角色体系重构、团队管理（含队长角色）、学生导入、团队数据仪表盘、学生个人详情、作业与公告系统。

---

### Phase 1 — 角色体系重构

**目标**：在原有 `is_staff / is_superuser` 基础上，新增业务级角色字段，支持 `student / teacher / admin` 三档权限。

#### 数据模型

`UserProfile`（扩展 `auth.User` 的 OneToOne 表）新增字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `role` | CharField | `student` / `teacher` / `admin`，默认 `student` |
| `student_id` | CharField | 学号（可空） |
| `major` | CharField | 专业（可空） |
| `grade` | CharField | 年级（可空） |
| `display_name` | CharField | 显示名（优先于 username） |
| `must_change_password` | BooleanField | 批量导入账号首次登录强制改密 |

#### API 变更

`/api/auth/me/` 返回新增 `role`、`must_change_password`、`display_name`、`student_id` 等字段，Pinia `userStore` 同步存储。

Router `beforeEach` 新增 `must_change_password` 拦截：已登录且未修改默认密码时，除 `/change-password` 外所有路由均重定向到修改密码页。

---

### Phase 2 — 团队管理系统

#### 新增模型

| 模型 | 关键字段 | 说明 |
|------|----------|------|
| `Team` | `name`, `creator`, `invite_code`, `is_active` | 班级/团队实体，创建者自动成为成员 |
| `TeamMembership` | `team`, `user`, `role`（`member`/`captain`）, `joined_at` | 团队成员关系，支持队长角色 |
| `TeamJoinRequest` | `team`, `user`, `status`（`pending`/`approved`/`rejected`）, `message` | 申请加入流程 |

`invite_code`：8 位随机字符串，教师可重置。

#### API 端点

```
POST   /api/teams/                    # 创建团队（教师/管理员）
GET    /api/teams/                    # 我管理的团队列表
GET    /api/my-teams/                 # 我加入的团队列表（学生用）
GET    /api/teams/<id>/               # 团队详情（含 can_manage / my_role）
PATCH  /api/teams/<id>/               # 更新团队信息
POST   /api/teams/<id>/join/          # 申请加入（用邀请码）
GET    /api/teams/<id>/members/       # 成员列表（含 can_manage）
POST   /api/teams/<id>/requests/      # 查看/审批申请列表
POST   /api/teams/<id>/reset-invite/  # 重置邀请码
DELETE /api/teams/<id>/members/<uid>/ # 移除成员
```

#### 权限设计

```python
def _is_team_viewer(user, team):
    # 团队创建者、管理员、队长均可查看
    ...

def _is_creator_or_admin(user, team):
    # 仅创建者或 admin 可进行管理操作
    ...
```

`TeamDetailAPIView.get()` 返回 `can_manage`（创建者/admin 为 True，队长为 False）和 `my_role`（`member`/`captain`/`creator`）。

---

### Phase 3 — 学生导入与强制改密

#### 单个学生添加

```
GET  /api/teams/<id>/search-student/  # 按用户名/姓名搜索已注册用户
POST /api/teams/<id>/add-student/     # 将现有用户加入团队（直接通过，无需审批）
```

#### Excel 批量导入

```
GET  /api/teams/<id>/import-template/  # 下载空白 xlsx 模板（含样例行）
POST /api/teams/<id>/import-students/  # 上传 xlsx 批量创建账号并加入团队
```

导入逻辑（`ImportStudentsAPIView`）：

1. `openpyxl` 读取工作表，按列：用户名、密码、姓名、学号、专业、年级
2. 账号不存在则 `User.objects.create_user()`，存在则直接加入团队
3. 新建账号设置 `UserProfile.must_change_password = True`
4. 返回 `{ created, added, skipped }` 三个计数

#### 强制改密流程

- **前端**：`ChangePasswordView.vue`，调用 `POST /api/auth/password/`（旧密码 + 新密码）
- 成功后 `userStore.fetchMe()` 拉取最新 profile，`must_change_password` 变为 `False`
- Router 守卫从 `userStore.user.must_change_password` 读取，自动放行

---

### Phase 4 — 团队仪表盘

#### 后端：`TeamDashboardAPIView`

```
GET /api/teams/<id>/dashboard/         # 统计数据
GET /api/teams/<id>/dashboard/export/  # 导出 Excel（openpyxl）
```

**核心函数 `_build_ranking_and_stats(team, member_user_ids, memberships)`：**

- **AC 去重**：全部使用 `distinct (user_id, problem_id)` 对，避免同题多次提交重复计数
- `total_ac`：全时间段去重 AC 数
- `week_ac`：最近 7 天去重 AC 数
- `month_ac`：最近 30 天去重 AC 数
- `by_group`：按难度分组（入门/普及/提高/NOI/其他）的 AC 分布

**`_build_trend(member_user_ids)`：**

30 天每日团队 AC 趋势，以 `(user_id, problem_id, TruncDate(created_at))` 三元组去重，反映有效日进展。

**统计卡片：**

```json
{
  "stats": {
    "member_count": 32,
    "total_ac": 847,
    "week_ac": 124,
    "avg_ac": "26.47",
    "pending_count": 3
  }
}
```

**Excel 导出**（`TeamDashboardExportAPIView`）：

`openpyxl` 写入排行表，含：排名、姓名、学号、总AC、本周AC、本月AC、各难度分组列，返回 `application/vnd.openxmlformats` blob。

#### 前端：`TeamDashboardView.vue`

- **统计卡片行**：5 张，待审核数 > 0 时显示橙色警告色
- **成员排行表**：3 个排序 tab（总排名/本周/本月），点击列头可切换排序，点击姓名跳转学生详情页
- **队长皇冠**：`role === 'captain'` 时显示 👑
- **ECharts 折线图**：30 天 AC 趋势，渐变填充，`vue-echarts` `CanvasRenderer`
- **导出按钮**：下载 blob 并触发浏览器另存为

```js
const { data: blob } = await exportDashboard(teamId)
const url = URL.createObjectURL(blob)
const a = document.createElement('a')
a.href = url; a.download = `${team.value.name}_ranking.xlsx`; a.click()
URL.revokeObjectURL(url)
```

---

### Phase 5 — 学生详情页

#### 后端：`TeamStudentDetailAPIView`

```
GET /api/teams/<teamId>/students/<userId>/
```

返回结构：

```json
{
  "member": { "display_name", "username", "student_id", "major", "grade", "total_ac", "total_submit" },
  "diff_dist": [{ "group": "入门", "count": 12 }, ...],
  "trend": [{ "date": "2026-05-11", "count": 3 }, ...],
  "heatmap": { "2026-01-15": 5, "2026-01-20": 2, ... },
  "ac_problems": [{ "problem_id", "title", "difficulty", "first_ac_at" }, ...]
}
```

- `diff_dist`：按 `_group_difficulty()` 分为 5 档，`DIFF_ORDER = ['入门','普及','提高','NOI','其他']`
- `trend`：近 30 天每日去重 AC（同 dashboard trend，但只统计该学生）
- `heatmap`：过去 365 天，按日汇总 AC 数（字典格式，前端直接遍历）
- `ac_problems`：最近 50 条去重 AC 记录，含首次通过时间

#### 前端：`StudentDetailView.vue`

- **顶部**：姓名、学号/专业/年级、AC 总数 + 总提交数（右上角）
- **难度分布**：ECharts 环形饼图（`PieChart`，`radius: ['45%','75%']`），右侧图例
- **30 天趋势**：ECharts 折线面积图（`LineChart`），与 dashboard 风格统一
- **过去一年热力图**：ECharts `HeatmapChart` + `CalendarComponent`，范围 `[today-365, today]`，颜色从 `#1e2030` 渐变到 `#a5b4fc`
- **AC 题目表格**：题号、标题、难度 tag（颜色徽章）、首次 AC 日期

---

### Phase 6 — 作业与公告系统

#### 新增模型

**`Announcement`：**

```python
class Announcement(models.Model):
    team = ForeignKey(Team)
    title = CharField(max_length=200)
    content = TextField(blank=True)
    is_pinned = BooleanField(default=False)
    created_by = ForeignKey(User)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-is_pinned', '-created_at']  # 置顶在前，新在前
```

**`Assignment`：**

```python
class Assignment(models.Model):
    team = ForeignKey(Team)
    title = CharField(max_length=200)
    description = TextField(blank=True)
    deadline = DateTimeField(null=True, blank=True)
    is_active = BooleanField(default=True)
    created_by = ForeignKey(User)
    ...
```

**`AssignmentProblem`：**

```python
class AssignmentProblem(models.Model):
    assignment = ForeignKey(Assignment)
    problem = ForeignKey(Problem)
    sort_order = IntegerField(default=0)
    class Meta:
        unique_together = ['assignment', 'problem']
        ordering = ['sort_order']
```

迁移文件 `0012_assignment_announcement.py` 自动生成，`python manage.py migrate` 应用成功。

#### API 端点

```
GET    /api/teams/<id>/announcements/         # 公告列表（成员可见）
POST   /api/teams/<id>/announcements/         # 创建公告（仅管理者）
PATCH  /api/teams/<id>/announcements/<aid>/   # 更新（含 togglePin）
DELETE /api/teams/<id>/announcements/<aid>/   # 删除

GET    /api/teams/<id>/assignments/           # 作业列表（含学生 AC 状态）
POST   /api/teams/<id>/assignments/           # 创建作业（仅管理者）
PATCH  /api/teams/<id>/assignments/<aid>/     # 更新（含题目列表）
DELETE /api/teams/<id>/assignments/<aid>/     # 删除
```

**`_assignment_data(assignment, user=None)`：**

为学生注入每道题的 `ac` 字段：

```python
if user:
    ac_set = set(Submission.objects.filter(
        user=user, status='AC', problem_id__in=pids
    ).values_list('problem_id', flat=True))
```

教师/管理员查看时 `user=None`，所有题目 `ac: False`（不显示完成情况，显示题目内容即可）。

#### 前端：`TeamDetailView.vue` 新增 Tab

教师管理界面新增两个 Tab（仅 `canManage=true` 时显示）：

**公告 Tab：**
- 公告列表，每条显示：标题、置顶状态（📌）、内容、创建时间
- 操作：新建、编辑（弹窗）、置顶/取消置顶（`PATCH is_pinned`）、删除

**作业 Tab：**
- 作业列表，显示题目数、截止时间
- 新建/编辑弹窗：标题、描述、截止日期、题目搜索添加（`/api/problems/?search=`）
- 题目列表可按 sort_order 排序，支持逐条删除

---

### Phase 7 — 队长只读视图（`can_manage`）

**设计原则**：队长可以查看团队信息、成员、仪表盘，但不能进行管理操作（审批、导入、重置邀请码、发公告、布置作业）。

#### 后端变更

所有涉及管理操作的接口使用 `_is_creator_or_admin()` 鉴权（而非 `_is_team_viewer()`），确保队长调用管理接口时返回 403。

三个 API 的响应均新增 `can_manage` 字段：

```python
# TeamDetailAPIView / TeamMembersAPIView / TeamDashboardAPIView
"can_manage": _is_creator_or_admin(request.user, team)
```

`TeamMembersAPIView` 响应格式从纯数组改为：

```json
{ "members": [...], "can_manage": true }
```

前端兼容处理：`members.value = ml.data.members ?? ml.data`

#### 前端变更（`TeamDetailView.vue`）

`canManage` ref 从 API 响应初始化：

```js
const { data: td } = await getTeam(teamId)
canManage.value = td.data.can_manage
```

以下元素加 `v-if="canManage"` 隐藏：

- 申请审批 Tab
- 添加学生 Tab
- 公告管理 Tab
- 作业管理 Tab
- 成员表格中的操作列（移除按钮）
- 邀请码重置按钮（队长只看到只读状态条）

#### 路由变更

`/teacher/teams/:id`、`/teacher/teams/:id/dashboard`、`/teacher/teams/:teamId/students/:userId` 三个路由移除 `requiresRole: 'teacher'`，改为仅 `requiresAuth: true`，权限校验下沉到后端 `_is_team_viewer()`。

#### 学生端队长快捷入口（`StudentTeamView.vue`）

```js
const isCaptain = computed(() => team.value?.my_role === 'captain')
```

`isCaptain` 为 True 时，顶部右侧显示"成员管理"和"团队排行 →"两个快捷按钮，直接跳转到对应的教师端页面。

---

### 新增文件汇总

| 文件 | 类型 | 说明 |
|------|------|------|
| `frontend/src/views/ChangePasswordView.vue` | Vue | 强制改密页（auto 账号首次登录） |
| `frontend/src/views/student/StudentTeamView.vue` | Vue | 学生端团队详情（公告+作业+队长快捷入口） |
| `frontend/src/views/teacher/TeamDashboardView.vue` | Vue | 团队总览仪表盘（统计卡+排行表+ECharts） |
| `frontend/src/views/teacher/StudentDetailView.vue` | Vue | 学生个人详情（饼图+折线+热力图+AC列表） |
| `judge/migrations/0012_assignment_announcement.py` | Django | 新增 Announcement / Assignment / AssignmentProblem 三表 |

### 主要修改文件汇总

| 文件 | 关键改动 |
|------|----------|
| `judge/models.py` | 新增 `Announcement` / `Assignment` / `AssignmentProblem` |
| `judge/team_api_views.py` | 新增 Dashboard / StudentDetail / Announcement / Assignment 全套 API |
| `judge/api_urls.py` | 注册以上所有新端点 |
| `frontend/src/api/team.js` | 新增 12 个 API 调用函数 |
| `frontend/src/views/teacher/TeamDetailView.vue` | 新增公告/作业 Tab，添加 `canManage` 控制显示/隐藏 |
| `frontend/src/views/student/MyTeamsView.vue` | 新增"公告/作业"入口按钮 |
| `frontend/src/router/index.js` | 新增 change-password / student-team 路由，移除教师团队路由的角色限制，增加 must_change_password 守卫 |

### 数据库状态

| 表 | 说明 |
|----|------|
| `judge_team` | 团队实体 |
| `judge_teammembership` | 成员关系（含队长角色） |
| `judge_teamjoinrequest` | 申请流程 |
| `judge_announcement` | 公告 |
| `judge_assignment` | 作业 |
| `judge_assignmentproblem` | 作业-题目关联表 |