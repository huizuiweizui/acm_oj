# ACM OJ — 算法竞赛在线评测平台

基于 Django + MySQL 的算法竞赛 Online Judge 平台，支持代码自动评测、ICPC/IOI 赛制比赛、讨论区、全站排行榜，并集成洛谷题目爬虫与 AI 代码评测反馈。

---

## 目录

- [技术栈](#技术栈)
- [功能清单](#功能清单)
- [项目结构](#项目结构)
- [核心数据模型](#核心数据模型)
- [快速开始](#快速开始)
- [洛谷题目爬虫](#洛谷题目爬虫)
- [评测系统](#评测系统)
- [AI 代码反馈](#ai-代码反馈)
- [管理后台](#管理后台)
- [界面设计](#界面设计)

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | Django 4.2 + Python 3.10+ | MTV 架构 |
| 数据库 | MySQL 8.0 (InnoDB) | utf8mb4 字符集 |
| 缓存 | Redis（可选） | 可用于排行榜加速 |
| 前端 | 原生 HTML / CSS / JS | 无前端框架依赖 |
| 代码编辑器 | Monaco Editor 0.45 | VS Code 同款编辑器 |
| Markdown | marked.js | 题目描述 / 讨论区渲染 |
| 数学公式 | KaTeX 0.16 | `$...$` 内联公式 |
| AI 反馈 | DeepSeek-V3 (SiliconFlow) | 提交后自动分析代码 |
| 爬虫 | requests + 自研重试机制 | 从洛谷批量导入题目 |

---

## 功能清单

### 题库

- 题目浏览（难度 / 标签 / 做题状态筛选 + 关键词搜索 + 分页）
- 8 级难度体系（对应洛谷：暂无评定 → 入门 → … → NOI/NOI+/CTSC）
- 题目详情页：左侧题面（Markdown + KaTeX）+ 右侧 Monaco 代码编辑器
- 自定义测试（不提交，直接运行查看输出）

### 评测

- 支持语言：C / C++ (C++17) / Java / Python
- 评测结果：AC / WA / TLE / MLE / RE / CE
- AJAX 提交 + 实时状态轮询
- AC 判重（同题同用户只计一次通过）
- AI 代码分析反馈（评测完成后异步生成）

### 比赛

- ICPC 赛制（AC 数降序 + 罚时升序）
- IOI 赛制（得分降序）
- 实时排行榜、比赛报名、题目编号（A/B/C…）

### 社区

- 讨论区（发帖 / 回复 / Markdown）
- 题目关联讨论（在题目详情页直接看讨论）
- 个人主页（AC 统计 / 提交历史 / 语言分布 / 比赛记录）
- 全站排行榜（AC 数 / Rating 两个维度）

### 其他

- Django Admin 管理后台（题目 CRUD / 测试数据 / 比赛管理）
- 暗黑 / 亮色双主题（CSS 变量驱动，偏好自动保存）
- 响应式布局，支持移动端

---

## 项目结构

```
acm_oj/
├── acm_oj/                         # Django 项目配置
│   ├── settings.py                 # 配置（数据库、评测、AI）
│   ├── urls.py                     # 根路由
│   └── wsgi.py
│
├── judge/                          # 主应用
│   ├── models.py                   # 10 张核心数据表
│   ├── views.py                    # 视图函数 + 评测引擎
│   ├── urls.py                     # 应用路由
│   ├── forms.py                    # 表单定义
│   ├── admin.py                    # Django Admin 注册
│   │
│   ├── templatetags/
│   │   └── judge_extras.py         # 自定义模板过滤器
│   │
│   ├── templates/judge/
│   │   ├── base.html               # 基础布局（导航 / 主题 / 字体）
│   │   ├── index.html              # 首页
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── problem_list.html       # 题库列表
│   │   ├── problem_detail.html     # 题目详情 + 编辑器
│   │   ├── submission_list.html    # 提交记录列表
│   │   ├── submission_detail.html  # 提交详情
│   │   ├── contest_list.html       # 比赛列表
│   │   ├── contest_detail.html     # 比赛详情
│   │   ├── contest_ranking.html    # 比赛排行榜
│   │   ├── leaderboard.html        # 全站排行榜
│   │   ├── profile.html            # 个人主页
│   │   ├── discussion_list.html    # 讨论区
│   │   ├── discussion_detail.html  # 帖子详情
│   │   └── create_discussion.html  # 发帖
│   │
│   ├── static/
│   │   ├── css/
│   │   │   ├── main.css            # 主样式（双主题 + 难度标签 + 组件）
│   │   │   └── problem_detail.css  # 题目页专用（全屏分栏 + 测试面板）
│   │   └── js/
│   │       ├── main.js             # 全局脚本（AJAX / Toast / Markdown）
│   │       ├── problem_detail.js   # 题目页脚本（Monaco / 提交 / 测试）
│   │       ├── theme-init.js       # 主题初始化（防闪烁）
│   │       └── theme-toggle.js     # 主题切换
│   │
│   └── management/commands/
│       └── crawl_luogu.py          # 洛谷题目爬虫
│
├── logs/                           # 爬虫运行日志（自动创建）
├── requirements.txt
└── README.md
```

---

## 核心数据模型

| 模型 | 表名 | 说明 |
|------|------|------|
| `UserProfile` | `judge_userprofile` | 用户扩展（角色 / AC 数 / Rating / 头像） |
| `Tag` | `judge_tag` | 算法标签（名称唯一） |
| `Problem` | `judge_problem` | 题目（Markdown 题面 / 8 级难度 / 时间内存限制） |
| `TestCase` | `judge_testcase` | 测试数据（输入 / 期望输出 / 是否样例） |
| `Submission` | `judge_submission` | 提交记录（代码 / 状态 / 耗时 / AI 反馈） |
| `Contest` | `judge_contest` | 比赛（ICPC/IOI / 公开 / 密码赛） |
| `ContestProblem` | `judge_contestproblem` | 比赛题目关联（编号 A/B/C…） |
| `ContestParticipant` | `judge_contestparticipant` | 参赛记录（得分 / 罚时） |
| `Discussion` | `judge_discussion` | 讨论帖（关联题目 / Markdown） |
| `DiscussionReply` | `judge_discussionreply` | 回复 |

### 难度等级

| 值 | 对应洛谷难度 | 徽章颜色 |
|----|------------|---------|
| `暂无评定` | 0 级 | 灰 |
| `入门` | 1 级 | 绿 |
| `普及-` | 2 级 | 青 |
| `普及/提高-` | 3 级 | 蓝 |
| `普及+/提高` | 4 级 | 紫 |
| `提高+/省选-` | 5 级 | 橙 |
| `省选/NOI-` | 6 级 | 红 |
| `NOI/NOI+/CTSC` | 7 级 | 深红 |

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

`requirements.txt` 主要依赖：

| 包 | 用途 |
|----|------|
| `Django>=4.2,<5.0` | Web 框架 |
| `mysqlclient>=2.2.0` | MySQL 驱动 |
| `requests>=2.31.0` | HTTP 客户端（爬虫） |
| `beautifulsoup4>=4.12.0` | HTML 解析（爬虫备用） |
| `django-redis>=5.4.0` | Redis 缓存（可选） |

### 2. 创建数据库

```sql
CREATE DATABASE acm_oj CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. 修改配置

编辑 `acm_oj/settings.py`，按实际情况修改以下字段：

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'acm_oj',
        'USER': 'root',
        'PASSWORD': '你的MySQL密码',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}
```

如需 AI 反馈功能，配置 LLM 接口：

```python
LLM_API_KEY  = '你的API密钥'
LLM_API_URL  = 'https://api.siliconflow.cn/v1/chat/completions'
LLM_MODEL    = 'deepseek-ai/DeepSeek-V3'
```

### 4. 初始化数据库

```bash
python manage.py makemigrations judge
python manage.py migrate
python manage.py createsuperuser   # 创建管理员账号
python manage.py runserver
```

### 5. 访问

| 地址 | 说明 |
|------|------|
| `http://127.0.0.1:8000/` | 前台首页 |
| `http://127.0.0.1:8000/admin/` | Django 管理后台 |

---

## 洛谷题目爬虫

`crawl_luogu` 命令从 [洛谷](https://www.luogu.com.cn/) 批量抓取题目并写入本站数据库。

- 通过率 / 提交数均以**本站真实提交**为准，爬取的洛谷数据不存入统计字段
- 难度标签与洛谷保持一致（8 个等级）
- 抓取来源标记为 `洛谷-PXXXX`，可通过 `--update` 覆盖更新

### 前置：获取 Cookie

爬虫需要洛谷登录 Cookie 才能正常访问题目 API（未登录时内容不完整）。

**获取步骤：**

1. 浏览器登录 [洛谷](https://www.luogu.com.cn/)
2. 打开开发者工具（F12）→ Network 标签页
3. 刷新任意洛谷页面，点击任意请求
4. 在 Request Headers 中找到 `Cookie` 字段，复制以下两个值：
   - `_uid`：你的用户 ID（纯数字）
   - `__client_id`：一串十六进制字符串

**配置方式一：环境变量（推荐）**

```bash
# Linux / macOS
export LUOGU_UID=你的_uid值
export LUOGU_CLIENT_ID=你的__client_id值

# Windows PowerShell
$env:LUOGU_UID = "你的_uid值"
$env:LUOGU_CLIENT_ID = "你的__client_id值"
```

**配置方式二：直接修改源码**

编辑 `judge/management/commands/crawl_luogu.py` 顶部的 `LUOGU_COOKIE`：

```python
LUOGU_COOKIE = {
    '_uid': '123456',                        # 替换为你的 _uid
    '__client_id': 'abcdef1234567890...',    # 替换为你的 __client_id
}
```

### 基本用法

```bash
# 爬取 200 道题（默认数量）
python manage.py crawl_luogu

# 指定爬取数量
python manage.py crawl_luogu --count 100

# 只爬取入门和普及- 难度（洛谷难度 1~2

# 强制更新已存在的题目
python manage.py crawl_luogu --update

# 从上次中断处继续（读取 logs/crawl_luogu_progress.json）
python manage.py crawl_luogu --resume

# 重试上次失败的题目
python manage.py crawl_luogu --retry-failed

# 从第 5 页开始爬
python manage.py crawl_luogu --start-page 5
```

### 全部选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--count N` | `200` | 目标爬取数量 |
| `--start-page N` | `1` | 从第 N 页开始（被 `--resume` 覆盖） |
| `--min-difficulty N` | `0` | 最低难度（0~7，对应暂无评定~NOI） |
| `--max-difficulty N` | `7` | 最高难度（0~7） |
| `--update` | 否 | 强制更新已存在的题目 |
| `--resume` | 否 | 从上次中断的页码继续 |
| `--retry-failed` | 否 | 只重试上次失败的题目 |

### 难度筛选参考

| `--min-difficulty` | `--max-difficulty` | 覆盖范围 |
|--------------------|--------------------|---------|
| 0 | 1 | 暂无评定 + 入门 |
| 1 | 3 | 入门 → 普及/提高- |
| 4 | 5 | 普及+/提高 + 提高+/省选- |
| 5 | 7 | 省选及以上 |

### 运行日志与进度

每次运行都会在 `logs/` 目录生成带时间戳的日志文件：

```
logs/
├── crawl_luogu_20250425_143022.log   # 详细日志
└── crawl_luogu_progress.json         # 进度存档（供 --resume 使用）
```

`progress.json` 结构：

```json
{
  "last_page": 12,
  "failed_pids": ["P1234", "P5678"],
  "updated_at": "2025-04-25T14:35:00"
}
```

### 典型场景

```bash
# 场景一：快速初始化题库（100 道入门题）
python manage.py crawl_luogu --count 100 --min-difficulty 1 --max-difficulty 2

# 场景二：爬取普及到省选的综合题库
python manage.py crawl_luogu --count 500 --min-difficulty 2 --max-difficulty 6

# 场景三：爬取中断后恢复
python manage.py crawl_luogu --count 500 --resume

# 场景四：定期增量更新已有题目
python manage.py crawl_luogu --count 50 --update

# 场景五：网络不稳定后重试失败题目
python manage.py crawl_luogu --retry-failed
```

### 爬虫内置保护机制

| 机制 | 说明 |
|------|------|
| 请求间隔 | 每道题随机等待 1.5~3.5 秒 |
| 额外休息 | 每爬 20 道额外休息 3~6 秒 |
| 自动重试 | 429 / 5xx / 网络异常自动指数退避重试，最多 3 次 |
| 进度持久化 | 每 10 道自动保存进度，中断不丢 |
| 失败收集 | 失败 PID 写入进度文件，`--retry-failed` 一键重跑 |

### 故障排查

| 现象 | 原因 | 解决方法 |
|------|------|---------|
| 第一步获取不到题目 | Cookie 失效或未配置 | 重新获取浏览器 Cookie |
| 大量题目内容为空 | 未登录状态返回不完整数据 | 确认 Cookie 配置正确 |
| 频繁 429 错误 | 请求过快被限流 | 适当增大 `DELAY_MIN`/`DELAY_MAX`（脚本顶部常量） |
| 数据库写入报错 | 超级用户不存在 | 先执行 `python manage.py createsuperuser` |
| 中途中断想继续 | — | 使用 `--resume` 参数 |

---

## 评测系统

评测引擎位于 `judge/views.py` 的 `judge_submission()` 函数，同步执行（无消息队列依赖）。

### 评测流程

```
用户提交代码
    ↓
写入数据库（状态: Pending）
    ↓
创建临时目录，写入源文件
    ↓
编译（gcc / g++ / javac / 跳过 Python）
    ↓ 编译失败 → CE，结束
    ↓ 编译成功
依次运行每个测试点
    ├── 超时 → TLE
    ├── 内存超限 → MLE
    ├── 运行崩溃 → RE
    └── 输出对比
        ├── 不一致 → WA
        └── 一致 → AC（该测试点通过）
    ↓
汇总结果，写入数据库
    ↓
AC 判重（同题同用户只计一次）
    ↓
比赛提交 → 自动计算 ICPC 罚时 / IOI 得分
    ↓
异步调用 AI 生成代码反馈
```

### 支持语言

| 语言 | 编译器 | 标准 | 说明 |
|------|--------|------|------|
| C | `gcc` | C11 | `-O2` 优化 |
| C++ | `g++` | C++17 | `-O2` 优化 |
| Java | `javac` / `java` | Java 11+ | 运行时加 `-Xmx256m` |
| Python | `python3` | 3.10+ | 解释执行，无需编译 |

### 评测结果

| 状态 | 说明 |
|------|------|
| `AC` | Accepted，全部测试点通过 |
| `WA` | Wrong Answer，输出与期望不符 |
| `TLE` | Time Limit Exceeded，超时 |
| `MLE` | Memory Limit Exceeded，超内存 |
| `RE` | Runtime Error，运行崩溃 |
| `CE` | Compilation Error，编译失败 |

### 相关配置

```python
# acm_oj/settings.py
JUDGE_TEMP_DIR = os.path.join(BASE_DIR, 'judge_tmp')  # 临时文件目录
JUDGE_TIMEOUT  = 10   # 全局评测超时（秒），题目 time_limit 为单测试点限制
```

---

## AI 代码反馈

每次提交评测完成后，系统会调用 LLM 接口对代码进行分析，结果展示在提交详情页。

**分析内容：**
- 代码正确性分析（针对 WA/RE/TLE 给出可能原因）
- 算法思路评价
- 可改进建议（时间/空间复杂度优化方向）

**配置：**

```python
# acm_oj/settings.py
LLM_API_KEY = '你的密钥'
LLM_API_URL = 'https://api.siliconflow.cn/v1/chat/completions'
LLM_MODEL   = 'deepseek-ai/DeepSeek-V3'
```

> 如不需要 AI 反馈，将 `LLM_API_KEY` 置为空字符串即可，评测不受影响。

---

## 管理后台

访问 `http://127.0.0.1:8000/admin/`，使用超级用户账号登录。

| 模块 | 功能 |
|------|------|
| 题目管理 | 创建 / 编辑 / 删除题目，内联编辑测试数据 |
| 标签管理 | 添加 / 合并算法标签 |
| 比赛管理 | 创建比赛、添加题目、管理参赛者 |
| 提交记录 | 查看所有提交，代码只读 |
| 用户管理 | 修改角色（普通用户 / 管理员）、查看 AC 数 |
| 讨论管理 | 删除违规帖子 |

### 在后台添加测试数据

1. 进入 **题目** 列表，点击题目进入编辑页
2. 页面下方有 **测试数据** 内联表单
3. 每行填写「输入数据」和「期望输出」
4. 勾选「是否样例」可作为样例展示在题目页面
5. `sort_order` 控制测试点顺序（从小到大依次执行）

---

## 界面设计

### 主题

- **暗黑模式**（默认）+ **亮色模式**，通过右上角按钮切换，偏好保存至 `localStorage`
- CSS 变量驱动，所有颜色统一在 `main.css` `:root` 和 `[data-theme="light"]` 中定义

### 核心色系

| 变量 | 含义 | 暗色值 |
|------|------|--------|
| `--accent` | 主色（靛青） | `#4F46E5` |
| `--green` | 成功 / AC | `#34d399` |
| `--red` | 错误 / WA | `#f87171` |
| `--orange` | 警告 / TLE | `#fb923c` |
| `--text-primary` | 正文 | `#e2e8f0` |
| `--bg-card` | 卡片背景 | `#1e293b` |

### 字体

- **中文正文**：Noto Sans SC（Google Fonts）
- **代码 / 等宽**：JetBrains Mono（Google Fonts）

### 难度徽章

难度徽章样式参考洛谷，左侧实色条 + 浅色背景 + 彩色边框：

```
┌───────────────────┐
│▌ 入门             │   ← 左侧 5px 实色条 + 淡绿背景 + 绿色细边框
└───────────────────┘
```
