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
