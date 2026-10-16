# 阶段二十：星语完整问卷与界面定制、skills 合入、三端教学功能补全

分支：`feat/star-integration`（基于 `feat/star`）。

## 一、合入 feat/star-skills

- 合并 `feat/star-skills`（6 个对话处理 skill，纯 Python 包 `star/skills/`），唯一冲突在 `requirements.txt`，两边依赖都保留（新增 `jieba`）
- skills 自带 32 个单元测试全部通过（`python -m unittest discover -s star/skills/tests -t .`）
- 目前只合入了代码包，`star/services/assistant.py` 仍用自己的仿说检测与词表替换；是否改走 skills 的 `InputPipeline` 待负责人确认

## 二、问卷改为负责人给的完整版本（`star/services/profile.py`）

负责人确认的口径：题目全部上；第 14 题补全；兴趣题扩充；按学生选的颜色定制界面；打分题用色块 / 形状配 1–5 档表情；统一第一人称"我"。

| 项 | 做法 |
| --- | --- |
| 题量 | 19 屏：问卷文本 14 题全部保留；原有的陪填人、兴趣、阅读、打字、节奏 5 题保留（层级判定与任务主题依赖它们）；原"看图还是看字"并入"学新东西更喜欢"多选题 |
| 题型 | `single` 单选 / `multi` 多选 / `scale` 打分表；选项可带 `other` 自填（≤20 字，存 `<key>_other`） |
| 打分表 | 颜色题每行一个色块、形状题每行一个 SVG 图形，配 😍🙂😐🙁😣 五档；界面需求题用 很需要 / 有点需要 / 都可以 / 不需要 四档 |
| 第 14 题 | 补为：愿意自己再试一试 / 需要有人鼓励一下 / 先看看提示 / 去问老师 / 先休息一下再来 |
| 兴趣 | 新增机器人、飞机、音乐、踢球，并补齐闯关主题包（`content/levels.py THEMES`）与引导对话选项 |

## 三、按问卷定制学生端界面

`profile.build_ui(survey)` 纯规则换算，写入画像 `ui` 字段（不交给大模型）：

- 背景：问卷选的背景色（白 / 浅灰 / 浅蓝 / 浅绿 / 深色；"都可以"用默认米色）
- 主色：打分最高且 ≥"有点喜欢"的颜色（黑白灰不当主色），否则默认蓝
- 按钮：圆形 → 胶囊按钮，方形 → 直角，长方形 → 小圆角；最喜欢的形状作为选中标记（● ■ ▬ ★ ♥ ▲）
- 只有说"需要调字号 / 想自己选颜色"的学生，页头才出现 A−/A+ 和换色按钮（选择存本机）

前端 `components/star/starUi.js` 把 `ui` 换成 CSS 变量，作用于星语学生端三个页面；交卷后立即生效。
所有色值为低饱和、白字对比度足够的版本，深色背景下文字主色自动换浅色版本。
定制在填完问卷时定一次，之后不变（符合坚持同一性）。教师端学生详情页显示问卷全部答案和定制结果。

## 四、三端教学功能补全（从 master 上的修复移植）

- 修复：普通成员看公告 / 作业 403（学生团队页空白）；Excel 导入后成员列表被清空、失败原因不显示；作业搜题参数错误；截止时间时区偏移；提交列表用户链接 `/users/undefined`
- 团队总览：全部 / 本周 / 本月 / 自定义时间筛选，8 级难度列，总提交、AC 率、最近活跃，任意列排序、并列名次，按筛选导出
- 学生详情：知识点（Tag）下钻，未 AC 题标红并排前，点题目跳该生提交记录
- 作业：`start_at` 时间窗，按时 / 补交判定，完成矩阵页与导出，队长只读
- 学生端：团队内排行、我的名次、作业倒计时、公告 Markdown
- 新页面：提交详情、404；`seed_demo` 演示数据；`DB_ENGINE=sqlite` 本地开关
- 迁移 `0016_assignment_start_at_submission_index`

## 五、测试

```bash
DB_ENGINE=sqlite SECRET_KEY=test python manage.py test judge star   # 232 个，9 个跳过（MySQL 专属 / 需外部服务）
```

新增 `judge/tests/test_team.py`（15 个）与 `star/tests/test_survey.py`（13 个），`test_api` 增加界面定制用例。
`JudgeTaskConnectionTests` 依赖 MySQL 的 `CONNECTION_ID()`，SQLite 下自动跳过。
