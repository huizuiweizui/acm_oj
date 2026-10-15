"""
消融实验的测试数据。

!!! 意图标注是初稿 !!!
任务书要求"测试语句初稿可由大模型生成，但意图标注须经人工逐条核对，以避免由大模型自行评价自身"。
下面 50 条语句和标注由开发者起草，正式跑测试、写进测试报告之前，请逐条核对 label，
核对完把 REVIEWED 改为 True（star_eval 在 REVIEWED=False 时会在结果里标注"未经人工核对"）。

意图取值见 services/validators.INTENTS：
    ask_hint 想要提示 / not_understand 没听懂 / repeat 再说一遍 / done 做完了 / rest 想休息
    chat 聊兴趣 / help 需要老师 / echo 仿说 / other 其他
"""

REVIEWED = False

# 测试用的虚构学习者词表（自创词 → 标准说法）
EVAL_VOCABULARY = [
    {'word': '亮亮', 'meaning': '提示'},
    {'word': '咕噜', 'meaning': '不懂'},
    {'word': '停停', 'meaning': '想休息'},
    {'word': '黑黑', 'meaning': '休息'},
    {'word': '好了好了', 'meaning': '做完了'},
    {'word': '呜呜', 'meaning': '火车'},
    {'word': '大长脖', 'meaning': '腕龙'},
    {'word': '飞飞', 'meaning': '火箭'},
]

DEFAULT_LAST_BOT = '{name}，现在想做什么？'

# category: echolalia 仿说 15 条 / pronoun 代词逆转 15 条 / neologism 自创词 10 条 / plain 普通表达 10 条
INTENT_CASES = [
    # ── 仿说：原样或部分重复系统上一句 ──
    {'category': 'echolalia', 'last_bot': '{name}，你想看提示吗？', 'text': '你想看提示吗', 'label': 'echo'},
    {'category': 'echolalia', 'last_bot': '我们先读入两个数。', 'text': '我们先读入两个数', 'label': 'echo'},
    {'category': 'echolalia', 'last_bot': '要不要休息一下？', 'text': '要不要休息一下', 'label': 'echo'},
    {'category': 'echolalia', 'last_bot': '这一步要排代码。', 'text': '要排代码', 'label': 'echo'},
    {'category': 'echolalia', 'last_bot': '点一下前进卡片。', 'text': '前进卡片', 'label': 'echo'},
    {'category': 'echolalia', 'last_bot': '小火车要去车站。', 'text': '小火车要去车站', 'label': 'echo'},
    {'category': 'echolalia', 'last_bot': '先看第一条提示。', 'text': '第一条提示', 'label': 'echo'},
    {'category': 'echolalia', 'last_bot': '你做完这一步了吗？', 'text': '做完这一步了吗', 'label': 'echo'},
    {'category': 'echolalia', 'last_bot': '用重复卡试一试。', 'text': '重复卡试一试', 'label': 'echo'},
    {'category': 'echolalia', 'last_bot': '我们一起看题目。', 'text': '一起看题目', 'label': 'echo'},
    {'category': 'echolalia', 'last_bot': '现在是第二步。', 'text': '现在是第二步', 'label': 'echo'},
    {'category': 'echolalia', 'last_bot': '想一想 4 除以 2。', 'text': '4 除以 2', 'label': 'echo'},
    {'category': 'echolalia', 'last_bot': '要再说一遍吗？', 'text': '再说一遍吗', 'label': 'echo'},
    {'category': 'echolalia', 'last_bot': '把代码排好顺序。', 'text': '排好顺序', 'label': 'echo'},
    {'category': 'echolalia', 'last_bot': '请点一个按钮。', 'text': '请点一个按钮', 'label': 'echo'},

    # ── 代词逆转：用"你"指自己 ──
    {'category': 'pronoun', 'text': '你要提示', 'label': 'ask_hint'},
    {'category': 'pronoun', 'text': '你不会', 'label': 'not_understand'},
    {'category': 'pronoun', 'text': '你累了', 'label': 'rest'},
    {'category': 'pronoun', 'text': '你做完了', 'label': 'done'},
    {'category': 'pronoun', 'text': '你想休息', 'label': 'rest'},
    {'category': 'pronoun', 'text': '你不知道怎么排', 'label': 'not_understand'},
    {'category': 'pronoun', 'text': '你肚子疼', 'label': 'help'},
    {'category': 'pronoun', 'text': '你喜欢恐龙', 'label': 'chat'},
    {'category': 'pronoun', 'text': '你写好了', 'label': 'done'},
    {'category': 'pronoun', 'text': '你要看提示', 'label': 'ask_hint'},
    {'category': 'pronoun', 'text': '你听不懂', 'label': 'not_understand'},
    {'category': 'pronoun', 'text': '你不想做了', 'label': 'rest'},
    {'category': 'pronoun', 'text': '你要找老师', 'label': 'help'},
    {'category': 'pronoun', 'text': '你想讲火车', 'label': 'chat'},
    {'category': 'pronoun', 'text': '你又错了，你要帮忙', 'label': 'ask_hint'},

    # ── 自创词：需要个人词表才能理解 ──
    {'category': 'neologism', 'text': '要亮亮', 'label': 'ask_hint'},
    {'category': 'neologism', 'text': '咕噜', 'label': 'not_understand'},
    {'category': 'neologism', 'text': '停停', 'label': 'rest'},
    {'category': 'neologism', 'text': '好了好了', 'label': 'done'},
    {'category': 'neologism', 'text': '呜呜呜呜', 'label': 'chat'},
    {'category': 'neologism', 'text': '大长脖', 'label': 'chat'},
    {'category': 'neologism', 'text': '黑黑', 'label': 'rest'},
    {'category': 'neologism', 'text': '亮亮在哪', 'label': 'ask_hint'},
    {'category': 'neologism', 'text': '咕噜了', 'label': 'not_understand'},
    {'category': 'neologism', 'text': '飞飞好看', 'label': 'chat'},

    # ── 普通表达 ──
    {'category': 'plain', 'text': '我想看提示', 'label': 'ask_hint'},
    {'category': 'plain', 'text': '我不懂这一步', 'label': 'not_understand'},
    {'category': 'plain', 'text': '请再说一遍', 'label': 'repeat'},
    {'category': 'plain', 'text': '我做完了', 'label': 'done'},
    {'category': 'plain', 'text': '我想休息一下', 'label': 'rest'},
    {'category': 'plain', 'text': '我喜欢恐龙', 'label': 'chat'},
    {'category': 'plain', 'text': '我要找老师', 'label': 'help'},
    {'category': 'plain', 'text': '第二个选项对吗', 'label': 'ask_hint'},
    {'category': 'plain', 'text': '什么意思', 'label': 'not_understand'},
    {'category': 'plain', 'text': '我头疼', 'label': 'help'},
]

# 回答一致性：10 个问题，每个问 5 次
CONSISTENCY_QUESTIONS = [
    'for 循环是什么？',
    'range(1, n + 1) 是什么意思？',
    '为什么要缩进？',
    'print 是做什么的？',
    '我该先做哪一步？',
    '这个题怎么开始？',
    'if 和 else 有什么不同？',
    '变量是什么？',
    '% 是什么符号？',
    '怎么用重复卡？',
]
