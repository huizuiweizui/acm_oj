# ACM OJ — 算法竞赛在线评测平台

基于 Django + MySQL 的 ACM 算法竞赛 Online Judge 平台，支持代码提交与自动评测、ICPC/IOI 赛制比赛、排行榜、讨论区等功能。

## 技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| 后端 | Django 4.2 + Python 3.10+ | MTV 架构 |
| 数据库 | MySQL 8.0 (InnoDB) | 关系型主库 |
| 缓存 | Redis（可选） | 排行榜/评测队列 |
| 前端 | 原生 HTML/CSS/JS | 极简主义 + Material Design |
| 评测 | 子进程 + timeout | 编译运行用户代码，对比输出 |

## 设计风格

- **极简主义 + 卡片式设计**：大量留白、清晰信息分区、克制配色
- **Material Design**：涟漪按钮反馈、统一表单/导航组件
- **暗黑/亮色双主题**：CSS 变量驱动，自动保存偏好
- **玻璃拟态**：统计面板、个人主页等局部毛玻璃效果
- **配色**：靛青 #4F46E5 主色 + 绿/红/橙语义色
- **字体**：Noto Sans SC（中文）+ JetBrains Mono（代码）

## 项目结构

```
acm_oj/
├── acm_oj/                  # Django 项目配置
│   ├── settings.py          # 配置文件（数据库、评测、AI）
│   ├── urls.py              # 根路由
│   └── wsgi.py
├── judge/                   # 主应用
│   ├── models.py            # 数据模型（10 张核心表）
│   ├── views.py             # 视图函数（含评测引擎）
│   ├── urls.py              # 应用路由
│   ├── forms.py             # 表单定义
│   ├── admin.py             # 后台管理
│   ├── templatetags/        # 自定义模板标签
│   ├── templates/judge/     # HTML 模板
│   │   ├── base.html                # 基础布局
│   │   ├── index.html               # 首页
│   │   ├── login.html / register.html
│   │   ├── problem_list.html        # 题库
│   │   ├── problem_detail.html      # 题目详情 + 代码编辑器
│   │   ├── submission_list.html     # 提交记录
│   │   ├── submission_detail.html   # 提交详情
│   │   ├── contest_list.html        # 比赛列表
│   │   ├── contest_detail.html      # 比赛详情
│   │   ├── contest_ranking.html     # 比赛排行榜
│   │   ├── leaderboard.html         # 全站排行榜
│   │   ├── profile.html             # 个人主页
│   │   ├── discussion_list.html     # 讨论区
│   │   ├── discussion_detail.html   # 讨论详情
│   │   └── create_discussion.html   # 发帖
│   ├── static/
│   │   ├── css/main.css     # 主样式（双主题 + 玻璃拟态）
│   │   └── js/
│   │       ├── main.js      # 全局脚本（AJAX提交/Toast/涟漪）
│   │       ├── theme-init.js
│   │       └── theme-toggle.js
│   └── management/commands/
│       └── seed_data.py     # 示例数据导入
├── manage.py
├── requirements.txt
└── README.md
```

## 核心数据表

| 表 | 说明 |
|----|------|
| UserProfile | 用户扩展（角色/AC数/Rating） |
| Problem | 题目（Markdown题面/难度/限制） |
| Tag | 标签（DP/图论/贪心等） |
| TestCase | 测试数据（输入/期望输出） |
| Submission | 提交记录（AC/WA/TLE/MLE/RE/CE） |
| Contest | 比赛（ICPC/IOI赛制） |
| ContestProblem | 比赛题目（编号A/B/C） |
| ContestParticipant | 比赛参与者（得分/罚时） |
| Discussion | 讨论帖 |
| DiscussionReply | 讨论回复 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 创建 MySQL 数据库

```sql
CREATE DATABASE acm_oj CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. 修改配置

编辑 `acm_oj/settings.py`，修改数据库密码：

```python
DATABASES = {
    'default': {
        ...
        'PASSWORD': '你的MySQL密码',
        ...
    }
}
```

### 4. 初始化

```bash
python manage.py makemigrations judge
python manage.py migrate
python manage.py seed_data      # 导入示例数据（含管理员 admin/admin123）
python manage.py runserver
```

### 5. 访问

- 前台：http://127.0.0.1:8000/
- 管理后台：http://127.0.0.1:8000/admin/

## 评测系统

评测引擎位于 `judge/views.py` 的 `judge_submission()` 函数。流程：

1. 用户提交代码 → 存入数据库，状态 Pending
2. 将源代码写入临时文件，调用编译器（gcc/g++/javac）
3. 编译失败 → 返回 CE
4. 编译成功 → 依次运行每个测试点，用 `timeout` 限制时间
5. 对比输出与期望输出 → 判定 AC/WA/TLE/MLE/RE
6. 更新统计（AC 判重：同用户同题目只计一次）
7. 比赛提交自动计算 ICPC 罚时

**支持语言：** C / C++ (C++17) / Java / Python

## 功能清单

- [x] 用户注册/登录（Django Auth）
- [x] 题库浏览（难度/标签/状态筛选 + 搜索 + 分页）
- [x] 题目详情（左右分栏：题面 + 代码编辑器）
- [x] 代码提交与评测（AJAX + 实时反馈）
- [x] 评测状态：AC/WA/TLE/MLE/RE/CE
- [x] 比赛系统（ICPC/IOI 赛制）
- [x] 比赛报名/实时排行榜/罚时计算
- [x] 全站排行榜（AC数/Rating）
- [x] 讨论区（发帖/回复/Markdown）
- [x] 个人主页（AC题目/提交历史/语言分布/比赛记录）
- [x] 管理后台（Django Admin：题目CRUD/测试数据/比赛管理）
- [x] 暗黑/亮色双主题切换
- [x] 响应式移动端适配
