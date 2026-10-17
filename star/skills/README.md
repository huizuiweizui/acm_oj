# 星语 skills

对话助手和题目改造链用到的 7 个处理模块。分工原则：**规则负责确定的事，大模型负责理解的事**。

这个包是纯 Python，不依赖 Django 和数据库，可以单独运行和测试，接入平台时只需要几行调用。

## 一览

| 顺序 | skill | 类型 | 做什么 | 文件 |
| --- | --- | --- | --- | --- |
| 1 | 分词与规范化 `segment` | 规则 | 统一全半角和空白；jieba 分词并标注词性；编程术语、卡片名、个人词表中的词整体保留 | `segment.py` |
| 2 | 仿说检测 `echo_detect` | 规则 | 判断学生是否在重复系统刚说的话；排除选项作答和正反问句的回答；是仿说时流程停止 | `echo.py` |
| 3 | 词表映射 `lexicon_map` | 规则 | 按个人词表把自创词换成标准词（精确、同音、相近三轮匹配）；找出候选新词交老师确认 | `lexicon.py` |
| 4 | 代词标注 `pronoun_tag` | 规则 | 找出“你、我、他”；画像标注了代词用法特点时，生成给大模型的理解提示 | `pronoun.py` |
| 5 | 表达记忆 `expr_memory` | 规则 | 和学生的个人表达记忆比对，说过的话直接给出记住的意图，不调大模型 | `memory.py` |
| 6 | 意图识别 `intent` | 大模型 | 结合以上结果判断学生想表达什么，输出固定格式 JSON；没有大模型时退回关键词规则 | `intent.py` |
| 7 | 字面化检查 `plain_check` | 规则 | 检查系统要展示的文字：句长、双重否定、反问、比喻成语、含糊词 | `plain_check.py` |

对应原始构想：词表映射即“自创词汇的专属知识库”，字面化检查即“重写”的质量把关，代词标注即“代词逆转”的处理。
表达记忆针对刻板语言：学生常反复用同一句话表达同一个意思，记住之后每次都按同一个意思理解。

## 处理流程

```
学生输入 → 分词 → 仿说检测 ─(是仿说)→ 换一种问法，用选项按钮重问
                    │
                    └(不是)→ 词表映射 → 代词标注 → 表达记忆 ─(命中)→ 直接用记住的意图
                                                      │
                                                      └(没命中)→ 意图识别 → 系统生成回复 → 字面化检查 → 展示
```

调用顺序固定，不让大模型自己选择调用哪个 skill：结果稳定、便于测试，也符合“坚持同一性”的设计要求。
每个 skill 都提供 `describe()`，以后如果改成由大模型通过函数调用自行选择，可以直接作为工具说明。

## 快速开始

```bash
pip install jieba            # 必需（requirements.txt 已列出）
pip install pypinyin         # 可选，打开同音匹配（“乌乌车”对上“呜呜车”）

python -m star.skills.demo --pinyin                          # 看一遍处理过程（不调用大模型）
python -m unittest discover -s star/skills/tests -t . -v     # 运行全部测试
python -m star.skills.eval_intent --pinyin                   # 消融实验示例
```

以上命令在项目根目录（`manage.py` 所在目录）执行。
`demo` 和 `eval_intent` 加 `--llm` 会读取环境变量 `LLM_API_KEY / LLM_API_URL / LLM_MODEL` 调用大模型。
如果安装 jieba 时报 setuptools 相关错误，先执行 `pip install -U setuptools wheel`。

jieba 是硬依赖（`segment.py` 在模块顶层 `import jieba`）。没装时不只是本包跑不起来：
`python manage.py test star` 会把 `star/skills/tests` 一起收进去，发现阶段就报 `star.skills` 导入失败。
`star/services/` 不依赖本包，所以星语其他部分的测试与功能不受影响。

## 在代码里使用

```python
from star.skills import InputPipeline, LearnerView, OpenAICompatClient, SkillContext, Turn, check_reply

llm = OpenAICompatClient.from_django_settings(on_call=save_llm_log)  # 沿用平台的 LLM_* 配置
pipe = InputPipeline(llm, use_pinyin=True)                          # 建议全局创建一次，重复使用

ctx = SkillContext(
    learner=LearnerView.from_dict(profile_json),                    # LearnerProfile 中的画像 JSON
    history=[Turn("system", "排好了吗？你也可以点提示。", options=[])],
    step_prompt="把三张卡片排成正确顺序，让小火车到达终点",
)
result = pipe.run("你要提示，呜呜车不走了", ctx)

result.intent           # {"intent": "ask_hint", "answer": "", "restated": "...", "confidence": 0.85, "source": "llm"}
result.text             # "你要提示,小火车不走了"（词表替换后的文本）
result.mappings         # [{"from": "呜呜车", "to": "小火车", "method": "exact", ...}]
result.candidate_words  # 候选新词，展示给老师确认后再加入词表
result.to_dict()        # 含每个 skill 的处理过程，可直接存库或返回给前端调试
```

### 画像 JSON 需要的字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `name` | 字符串 | 称呼，用于代词提示 |
| `level` | `"starter"` 或 `"entry"` | 启蒙层 / 入门层，决定字面化检查的句长上限（12 / 20 字） |
| `glossary` | 对象 | 个人词表，`{"自创词": "标准词"}` |
| `pronoun_reversal` | 布尔 | 你、我的用法和常规不同时为 true |
| `echolalia` | 布尔 | 常重复别人的话时为 true（目前仅记录，检测对所有人都开启） |
| `expressions` | 对象数组 | 已生效的表达记忆，`[{"text": "我要看一下", "intent": "ask_hint"}]`；`text` 用词表替换之后的说法 |
| `interests` | 字符串数组 | 兴趣，供题目改造使用 |

### 意图取值与建议的系统回应

| intent | 含义 | 建议的系统回应 |
| --- | --- | --- |
| `echo` | 仿说（流水线提前停止） | 换一种问法，改用选项按钮提问 |
| `answer` | 在作答 | 判断对错，给固定反馈 |
| `ask_hint` | 要提示 | 给下一级提示 |
| `dont_know` | 不会 | 给下一级提示，或把当前步骤再拆小 |
| `skip` | 想跳过 | 确认后跳过，记入作答记录 |
| `chat` | 闲聊 | 回应一句后拉回当前步骤 |
| `need_help` | 需要帮助 | 暂停学习，通知老师 |
| `unclear` | 无法判断 | 用选项按钮重新提问 |

`source` 表示结果来源：`option`（选了选项）、`yes_no`（回答正反问句）、`memory`（命中表达记忆）、`llm`、`llm_repaired`（大模型第一次输出不合格、修复后通过）、`rule`（关键词规则）。

### 检查系统要说的话

```python
res = check_reply("小火车在起点。放一张前进卡片。", ctx)
if not res["ok"]:
    # 把 res["violations"] 回填给大模型重新生成
    ...
res["stats"]   # {"sentences": 2, "avg_len": 6.0, "max_len": 7, "max_allowed": 12}，可用于改写前后对比
```

### 记录大模型调用

`OpenAICompatClient` 每次调用（包括失败和重试）都会把记录交给 `on_call`，字段有
`purpose / model / ok / error / attempt / latency_ms / usage / messages / response`，可直接写入 LLMCallLog 表：

```python
def save_llm_log(rec):
    LLMCallLog.objects.create(purpose=rec["purpose"], ok=rec["ok"], attempt=rec["attempt"],
                              latency_ms=rec["latency_ms"], usage=rec["usage"],
                              request=rec["messages"], response=rec["response"], error=rec["error"])
```

## 消融实验

```python
from star.skills import COMM_SKILLS, InputPipeline
pipe_full = InputPipeline(llm)
pipe_ablation = InputPipeline(llm, disabled=COMM_SKILLS)  # 关闭仿说检测、词表映射、代词标注、表达记忆
```

`eval_intent.py` 已经实现了对比统计。自带的 14 条样例在关键词规则模式下的结果（仅演示格式）：

| 类别 | 关闭沟通特征处理 | 开启全部 skill |
| --- | --- | --- |
| 仿说 | 0/4 | 4/4 |
| 代词逆转 | 2/3 | 2/3 |
| 自创词 | 0/3 | 2/3 |
| 普通表达 | 3/4 | 3/4 |
| 合计 | 5/14 | 11/14 |

正式测试需要准备 50 条语句（格式见 `data/intent_samples.jsonl`），人工逐条核对标注后，用 `--llm` 运行。

## 可调参数

| 参数 | 默认值 | 位置 |
| --- | --- | --- |
| 仿说相似度阈值 | 0.85 | `InputPipeline(echo_threshold=...)` |
| 相近匹配阈值 | 0.75 | `InputPipeline(fuzzy_threshold=...)` |
| 同音匹配开关 | 关 | `InputPipeline(use_pinyin=True)` |
| 表达记忆相近匹配阈值 | 0.85（且双方至少 4 字、否定词个数相同） | `memory.FUZZY_THRESHOLD` / `FUZZY_MIN_LEN` |
| 单句长度上限 | 启蒙 12 字 / 入门 20 字 | `plain_check.MAX_SENTENCE_LEN` |
| 生僻字词频线 | 1000 | `lexicon.RARE_CHAR_FREQ` |
| 编程术语词典 | 53 个词 | `data/terms.txt`（每行“词 词频 词性”） |

## 已知局限

- 只检测即时仿说（重复系统最近两句话），不检测延迟仿说（重复很久以前听到的话）。
- 关闭仿说检测时，选项作答和正反问句的规则判定也一起关闭。
- 候选新词基于生僻字和拟声词的启发式规则，会有漏报和误报，所以必须由老师确认。
- 代词提示只在画像中做了标注后生效，系统不会自己推断学生的沟通特点。
- 表达记忆只认很接近的说法：短句（不到 4 个字）必须去掉标点和句末语气词后完全相同；换一种说法不会命中，会正常走意图识别。
- 表达记忆不记作答（`answer`），因为答案和当前题目有关；也不记仿说和无法判断。

## 与平台其他部分的关系

对话助手已经接入本包（见下面第 1 节）；题目改造链还没有接。

### 1. 对话助手 `star/services/assistant.py`（**已接入**）

`reply()` 按本文档的流程处理学生的每一句话：

```
求助护栏 → 分词 → 仿说检测 → 词表映射 → 代词标注 → 意图识别（大模型 P5）
        → 系统生成回复（大模型 P3）→ 结构校验 + 字面化检查（不合格回填改一次）→ 展示
```

- 规则部分（分词到表达记忆）用 `InputPipeline(None, disabled={"intent"})` 先跑；意图识别单独调 `IntentSkill`。
  这样同一学生在同一步骤问同一句话时，回复和意图一起从缓存取，不再调大模型。
- 表达记忆存在 `LearnerProfile.expressions`，读写在 `star/services/expressions.py`：大模型识别出可记忆的意图、
  置信度 ≥ 0.8 时记一票，同一句话两次得到同一意图才生效；教师在"对话记录"页可以改意思、确认、删除、手动添加，
  教师确认或添加的立即生效。教师改了某句话的意思后，这句话的旧回复缓存不再使用。
- 仿说阈值统一为平台原来的 **0.8**（本包默认 0.85）；原来的"只复述上一句结尾"判定由本包的分句比较代替。
- 大模型走平台自己的 `star/services/llm.py`（适配类 `_PlatformLLM`）：发出前把姓名、昵称、用户名换成 `{name}`，
  每次调用写一条 `LLMCallLog`，意图识别的用途记为 **P5**。本包的 `OpenAICompatClient` 不做脱敏，平台里不用它。
- `intent` 为 `need_help` 时直接回"这件事请告诉老师"；仿说时不做意图识别，请模型换一种更简单的问法。
- 意图、词表替换、代词提示、候选新词都记进对话记录的 `meta`，教师端"对话"页逐条显示。
- 字面化检查按层级取句长上限（启蒙层 12 字 / 入门层 20 字），只把"错误"级问题回填给模型。
- 未配置大模型时：意图识别退回关键词规则，回复用固定的兜底话术。
- `assistant.is_echolalia / apply_vocabulary` 是接入前的简化实现，仍留给 `star_eval` 的消融实验做对照组。

### 2. 题目改造链 `star/services/adapt.py` / `validators.py`

本包 `check_reply()` 能多拦双重否定、反问、比喻成语、含糊词，`stats` 里的平均句长与最长句长
正好是任务书"改写前后句长对比"那张表的数据。`star/services/validators.py` 的 `check_reply` 只管
P3 回复的结构（一句话 + 2–4 个选项），两者互补，不是替代。

### 3. 算法问答的关键词检索（**已接入**）

`judge/services/rag.py` 在没有向量数据时退回关键词匹配。原来用 `query.split()`——中文没有空格，
整句被当成一个关键词，基本匹配不到。现在 `_query_keywords()` 用本包的分词：

    “二分查找的时间复杂度是多少” → ["二分查找", "时间复杂度"]

没装 jieba 时捕获 `ImportError` 后仍退回 `query.split()`，所以 RAG 页面不会因为缺依赖挂掉。
