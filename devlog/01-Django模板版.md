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
