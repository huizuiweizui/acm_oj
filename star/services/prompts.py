"""
四个提示词：
    P1 画像生成   问卷结果 + 引导对话记录            → 画像 JSON（层级、兴趣、呈现偏好、沟通特点、个人词表）
    P2 任务改造   原题或关卡模板 + 画像 + 层级 + 上次校验错误 → 关卡 JSON 或分步任务 JSON
    P3 对话辅导   画像 + 词表 + 当前步骤 + 处理后的学生输入   → 回复 JSON（意图 + 一句话 + 选项）
    P4 学习报告   作答记录统计                     → 面向教师 / 家长的文字报告

所有函数返回 OpenAI 格式的 messages 列表。学习者姓名一律以 {name} 出现（见 llm.redact），
提示词里也要求模型称呼学习者时写 {name}，输出回来再换成昵称。
"""
import json

from ..content.levels import THEMES
from . import maze
from .validators import INTENTS, KNOWLEDGE, SENTENCE_MAX, STEPS_MAX, STEPS_MIN, TITLE_MAX

_JSON_ONLY = '只输出 JSON，不要输出 JSON 以外的任何文字。'


def _dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1)


def profile_summary(profile, vocabulary=None):
    """把画像整理成几行中文，P2 / P3 共用。"""
    p = profile or {}
    comm = p.get('communication') or {}
    pres = p.get('presentation') or {}
    prefer = {'image': '喜欢看图', 'text': '喜欢看字', 'both': '图和字都可以'}.get(pres.get('prefer'), '未知')
    step = '一次只做一件小事，步骤要拆得更细' if pres.get('step_size') == 'small' else '步骤粒度正常'
    lines = [
        f'兴趣：{"、".join(p.get("interests") or []) or "未知"}',
        f'呈现偏好：{prefer}；{step}',
    ]
    notes = []
    if comm.get('pronoun_reversal'):
        notes.append('有时用"你"指自己、用"我"指对方')
    if comm.get('echolalia'):
        notes.append('有时会重复别人刚说的话')
    if comm.get('notes'):
        notes.append(comm['notes'])
    if notes:
        lines.append(f'沟通特点：{"；".join(notes)}')
    if vocabulary:
        lines.append('个人词表：' + '；'.join(f'"{v["word"]}"指{v["meaning"]}' for v in vocabulary))
    return '\n'.join(lines)


# ── P1 画像生成 ─────────────────────────────────────────────────────

P1_SYSTEM = f"""你是特殊教育学校的学习支持助手。请根据一名学习者的问卷答案和引导对话，整理一份"学习者画像"，供教师参考和确认。

规则：
1. 只整理与编程学习有关的信息：兴趣、喜欢的呈现方式、学习节奏、沟通时的说法。
2. 不做任何诊断，不推测病情，不评价情绪和性格。
3. 学习者的名字一律写成 {{name}}。
4. 个人词表只收学习者自己的特殊说法（自创词、对事物的独特叫法、表达"累了""不懂"的独特说法），每条写成 {{"word": 学习者的说法, "meaning": 对应的标准说法}}；普通词语不要收。
5. 层级：能读短句并且会打字的，建议 intro（入门层：分步学习代码）；否则建议 enlighten（启蒙层：指令卡片闯关）。
6. pronoun_reversal：对话中出现用"你"指自己、用"我"指对方时为 true。echolalia：回答原样重复了问题时为 true。拿不准就写 false，由教师判断。
7. {_JSON_ONLY}

输出格式：
{{
  "layer": "enlighten 或 intro",
  "layer_reason": "一句话说明理由，不超过 30 字",
  "interests": ["1 到 3 个兴趣词，每个不超过 8 字"],
  "presentation": {{"prefer": "image / text / both", "step_size": "small / normal"}},
  "communication": {{"pronoun_reversal": false, "echolalia": false, "notes": "沟通方面值得教师注意的地方，不超过 60 字，没有就写空字符串"}},
  "vocabulary": [{{"word": "...", "meaning": "..."}}]
}}"""


def p1_messages(survey_rows, dialogue_rows):
    """survey_rows: [(问题, 答案)]；dialogue_rows: [(问题, 答案)]，答案中的名字已替换为 {name}。"""
    survey = '\n'.join(f'{i}. {q} → {a}' for i, (q, a) in enumerate(survey_rows, 1))
    dialogue = '\n'.join(f'问：{q}\n答：{a}' for q, a in dialogue_rows) or '（未进行）'
    user = f'【问卷】\n{survey}\n\n【引导对话】\n{dialogue}\n\n请输出学习者画像 JSON。'
    return [{'role': 'system', 'content': P1_SYSTEM}, {'role': 'user', 'content': user}]


# ── P2 任务改造 ─────────────────────────────────────────────────────

P2_SYSTEM = f"""你是特殊教育编程课的任务设计助手，负责把通用的编程学习任务改造成孤独症学习者能够理解和完成的个体化任务。

设计依据（循证实践）：
· 任务分析：把复杂任务拆成小步骤，一步只练一个知识点；
· 结构化教学：固定流程，明确的开始和结束；
· 提示层级：每一步准备由少到多的三级提示，掌握后逐步撤除。

写作规则：
1. 只用短句，每句不超过 {SENTENCE_MAX} 字；表述字面、具体，不用比喻、反问、俗语和双重否定。
2. 用学习者的兴趣做主题，让任务和兴趣有关；但不改变题目要练的知识点。
3. 需要称呼学习者时写 {{name}}，不写真实姓名。
4. 先在 analysis 字段写知识点分析和拆解思路（学生看不到），再写任务内容。
5. 你的输出会被程序逐条检查，不合格会退回重写。
6. {_JSON_ONLY}"""

_LEVEL_RULES = f"""【关卡规则】
· 卡片：forward 前进一格；left / right 原地左转 / 右转；repeat 重复 N 次（N 取 2 到 5），只作用于紧跟在它后面的那一张卡片。
· 坐标：x 向右、y 向下，左上角是 (0, 0)；朝向用 N / E / S / W（上 / 右 / 下 / 左）。走到终点格就算成功。
· 地图不超过 8×8；起点、终点不能在障碍上。
· 必须能走通，且 最少卡片数 ≤ slots ≤ 最少卡片数 + 2。
· loop（循环）关卡：最短走法必须用到 repeat，并且不用 repeat 时放不进卡槽（把直线路段做长）。
· sequence（顺序）关卡：cards 里不放 repeat。
· 保留模板的 knowledge 和 cards；可以按兴趣改写标题、故事和图标，也可以调整起点、终点和障碍。
· title 不超过 {TITLE_MAX} 字；story 1 到 3 句；theme 的 hero / goal / wall 各是一个 emoji。

【输出格式】
{{"analysis": "...", "title": "...", "story": ["..."], "theme": {{"name": "主题名", "hero": "emoji", "goal": "emoji", "wall": "emoji"}},
 "grid": {{"w": 宽, "h": 高}}, "start": {{"x": 0, "y": 0, "dir": "E"}}, "goal": {{"x": 0, "y": 0}}, "walls": [[x, y]],
 "cards": ["forward"], "slots": 卡槽数, "knowledge": "sequence 或 loop"}}"""

_STEPS_RULES = f"""【分步任务规则】
· {STEPS_MIN} 到 {STEPS_MAX} 步。固定收尾：倒数第二步是排序题 order，最后一步是写代码 code。
· order：把参考解的全部代码行排成正确顺序。lines 逐字复制参考解的全部代码行（保留缩进，不增不减，顺序可以打乱）。
· code：学习者自己把整段程序写出来，程序会用测试数据实际运行。starter 是起始代码，
  只能放 # 开头的注释（每条是一个短句，说这一块要做什么）和参考解里原样的代码行，不能已经是完整答案；
  第一次写代码的学习者，starter 用注释把每一块要做的事列出来。
· choice：options 2 到 4 个且互不相同，answer 是唯一正确选项的下标（从 0 开始）。
· fill：code 是参考解中的某一行，把其中一小段换成 ____（四个下划线），answer 是被挖掉的内容。
· 每一步都有 hints：恰好 3 条，由少到多——第 1 条只提醒方向，第 2 条点出关键，第 3 条几乎给出答案。
· 每一步都有 knowledge：{" / ".join(f"{k}（{v}）" for k, v in KNOWLEDGE.items())} 之一。
· 不改动参考解的代码；主题只体现在文字里。
· title 不超过 {TITLE_MAX} 字；intro 1 到 3 句。

【输出格式】
{{"analysis": "...", "title": "...", "intro": ["..."], "theme": "主题词",
 "steps": [{{"type": "choice", "prompt": "...", "options": ["...", "..."], "answer": 0, "hints": ["...", "...", "..."], "knowledge": "sequence"}},
           {{"type": "fill", "prompt": "...", "code": "... ____ ...", "answer": "...", "hints": ["...", "...", "..."], "knowledge": "sequence"}},
           {{"type": "order", "prompt": "...", "lines": ["..."], "hints": ["...", "...", "..."], "knowledge": "sequence"}},
           {{"type": "code", "prompt": "...", "starter": "# ...\\n# ...\\n", "hints": ["...", "...", "..."], "knowledge": "sequence"}}]}}"""

# 少样本示例：各层一个，题目刻意不在素材库里，避免模型照抄答案
_LEVEL_EXAMPLE_IN = {
    'profile': '兴趣：恐龙\n呈现偏好：喜欢看图；一次只做一件小事，步骤要拆得更细',
    'template': {
        'title': '重复前进', 'story': ['路很长。', '用重复卡走过去。'],
        'grid': {'w': 5, 'h': 3}, 'start': {'x': 0, 'y': 1, 'dir': 'E'}, 'goal': {'x': 4, 'y': 1},
        'walls': [], 'cards': ['forward', 'repeat'], 'slots': 3, 'knowledge': 'loop',
    },
}
_LEVEL_EXAMPLE_OUT = {
    'analysis': '知识点是循环。直线有 4 格，"重复 4 次 + 前进"两张卡片就能走完；不用重复卡要 4 张，'
                '所以卡槽给 3 个，逼着用重复卡。主题用恐龙：小恐龙去找恐龙蛋；上下两侧放火山当障碍。',
    'title': '小恐龙找蛋',
    'story': ['小恐龙的蛋在前面。', '用重复卡走过去。'],
    'theme': {'name': '恐龙', 'hero': '🦕', 'goal': '🥚', 'wall': '🌋'},
    'grid': {'w': 5, 'h': 3}, 'start': {'x': 0, 'y': 1, 'dir': 'E'}, 'goal': {'x': 4, 'y': 1},
    'walls': [[2, 0], [2, 2]], 'cards': ['forward', 'repeat'], 'slots': 3, 'knowledge': 'loop',
}

_STEPS_EXAMPLE_IN = {
    'profile': '兴趣：火箭\n呈现偏好：图和字都可以；步骤粒度正常',
    'problem': '题目：是不是正数\n描述：输入一个整数 n，如果 n 大于 0，输出 yes，否则输出 no。',
    'code': 'n = int(input())\nif n > 0:\n    print("yes")\nelse:\n    print("no")\n',
}
_STEPS_EXAMPLE_OUT = {
    'analysis': '知识点是条件判断。拆成四步：先用具体数字理解"大于 0"，再写出判断条件，然后排好整段代码，'
                '最后自己写一遍；起始代码用注释列出三块要做的事。'
                '主题用火箭：n 是火箭的燃料，燃料大于 0 才能起飞。',
    'title': '火箭能起飞吗',
    'intro': ['火箭要有燃料才能飞。', '燃料大于 0 就能飞。'],
    'theme': '火箭',
    'steps': [
        {'type': 'choice', 'prompt': '燃料是 5，火箭能飞吗？', 'options': ['能飞', '不能飞'], 'answer': 0,
         'hints': ['5 比 0 大吗？', '5 大于 0。', '选能飞。'], 'knowledge': 'condition'},
        {'type': 'fill', 'prompt': '燃料 n 大于 0 才能飞。', 'code': 'if n ____ 0:', 'answer': '>',
         'hints': ['用一个比较符号。', '大于号的开口朝左。', '填 >。'], 'knowledge': 'condition'},
        {'type': 'order', 'prompt': '{name}，把代码排好。',
         'lines': ['else:', 'n = int(input())', '    print("no")', 'if n > 0:', '    print("yes")'],
         'hints': ['先读入燃料 n。', 'if 在 else 前面。', 'print 放在下面一行。'], 'knowledge': 'condition'},
        {'type': 'code', 'prompt': '{name}，自己把程序写出来。',
         'starter': '# 读入燃料 n\n\n# 燃料大于 0，输出 yes\n\n# 不然，输出 no\n',
         'hints': ['照着注释，一块一块写。', '和上一步排好的代码一样。', 'print 前面空四格。'], 'knowledge': 'condition'},
    ],
}

NEUTRAL_THEME = {'hero_name': '小机器人', 'goal_name': '终点'}


def _level_template_for_prompt(template):
    fill = {k: NEUTRAL_THEME[k] for k in ('hero_name', 'goal_name')}
    return {
        'title': template['title'].format(**fill),
        'story': [s.format(**fill) for s in template['story']],
        **{k: template[k] for k in ('grid', 'start', 'goal', 'walls', 'cards', 'slots', 'knowledge')},
    }


def p2_level_messages(profile_text, template, theme_key=''):
    th = THEMES.get(theme_key)
    theme_hint = f'\n可参考的主题图标：主角 {th["hero"]}，终点 {th["goal"]}，障碍 {th["wall"]}' if th else ''
    shortest = maze.shortest_solution(template)
    example_user = (f'【学习者画像】\n{_LEVEL_EXAMPLE_IN["profile"]}\n\n'
                    f'【关卡模板】\n{_dump(_LEVEL_EXAMPLE_IN["template"])}\n\n请输出改造后的关卡 JSON。')
    user = (f'【学习者画像】\n{profile_text}{theme_hint}\n\n'
            f'【关卡模板】（模板的最少卡片数是 {len(shortest) if shortest else "未知"}）\n'
            f'{_dump(_level_template_for_prompt(template))}\n\n请输出改造后的关卡 JSON。')
    return [
        {'role': 'system', 'content': f'{P2_SYSTEM}\n\n{_LEVEL_RULES}'},
        {'role': 'user', 'content': example_user},
        {'role': 'assistant', 'content': _dump(_LEVEL_EXAMPLE_OUT)},
        {'role': 'user', 'content': user},
    ]


def p2_steps_messages(profile_text, problem, code, step_size='normal'):
    granularity = ('这名学习者一次只做一件小事：拆成 5 到 6 步。' if step_size == 'small'
                   else '拆成 3 到 5 步。')
    example_user = (f'【学习者画像】\n{_STEPS_EXAMPLE_IN["profile"]}\n\n【原题】\n{_STEPS_EXAMPLE_IN["problem"]}\n\n'
                    f'【参考解（Python）】\n```python\n{_STEPS_EXAMPLE_IN["code"]}```\n\n请输出改造后的分步任务 JSON。')
    user = (f'【学习者画像】\n{profile_text}\n\n'
            f'【原题】\n题目：{problem["title"]}\n描述：{problem["description"]}\n'
            f'输入：{problem["input_desc"]}\n输出：{problem["output_desc"]}\n\n'
            f'【参考解（Python）】\n```python\n{code}```\n\n'
            f'{granularity}请输出改造后的分步任务 JSON。')
    return [
        {'role': 'system', 'content': f'{P2_SYSTEM}\n\n{_STEPS_RULES}'},
        {'role': 'user', 'content': example_user},
        {'role': 'assistant', 'content': _dump(_STEPS_EXAMPLE_OUT)},
        {'role': 'user', 'content': user},
    ]


def refine_message(errors):
    """修复轮：把校验错误回填给模型。"""
    items = '\n'.join(f'{i}. {e}' for i, e in enumerate(errors, 1))
    return (f'程序检查发现以下问题：\n{items}\n\n'
            f'请逐条修正，其余合格的部分保持不变，然后重新输出完整的 JSON。{_JSON_ONLY}')


# ── P3 对话辅导 ─────────────────────────────────────────────────────

_INTENT_TEXT = ' / '.join(f'{k}（{v}）' for k, v in INTENTS.items())

P3_SYSTEM = f"""你是"星语"编程学伴，正在辅导一名孤独症学习者学编程。

回复规则：
1. reply 只有一句话，不超过 20 个字；用字面、具体的说法，不用比喻和反问。
2. options 给 2 到 4 个选项，每个不超过 8 个字，让学习者点选回答。
3. 称呼学习者时写 {{name}}，不用其他称呼。
4. 不直接说出题目答案，可以引导学习者看提示、看题目或换一个具体的数字想一想。
5. 不做诊断，不评价情绪，不评价性格和表现好坏。
6. 学习者说到身体不舒服、害怕、被欺负、想回家等需要大人帮助的事，reply 写"这件事请告诉老师。"，options 写 ["找老师", "继续学习"]。
7. 同时判断学习者这句话的意图 intent，取值：{_INTENT_TEXT}。
8. {_JSON_ONLY}

输出格式：{{"intent": "...", "reply": "...", "options": ["...", "..."]}}"""


def p3_messages(profile_text, context_text, history, user_text, *, pronoun_note=False,
                echo_note=False, replaced=None, intent=None, pronoun_hints=None, max_len=20):
    system = f'{P3_SYSTEM}\n\n【学习者画像】\n{profile_text}'
    if max_len < 20:
        system += f'\n\n【句长】这名学习者在启蒙层：reply 不超过 {max_len} 个字。'
    if pronoun_note:
        system += ('\n\n【理解提示】这名学习者有时用"你"指自己、用"我"指对方。理解时按这个习惯推断真实意图，'
                   '例如"你要提示"通常是"我要提示"；不要纠正这种说法。')
    if context_text:
        system += f'\n\n【当前学习内容】\n{context_text}'
    messages = [{'role': 'system', 'content': system}]
    for turn in history:
        role = 'assistant' if turn['role'] == 'bot' else 'user'
        messages.append({'role': role, 'content': turn['text']})
    note = []
    if pronoun_hints:
        note.append('（代词提示：' + '；'.join(pronoun_hints) + '）')
    if intent and intent.get('intent'):
        note.append(f'（意图识别结果：{intent["intent"]}，{intent.get("restated") or ""}。'
                    f'回复要针对这个意图；仍按规则输出 intent 字段。）')
    if replaced:
        note.append('（已按个人词表把学习者的说法换成标准说法：'
                    + '；'.join(f'"{w}"→"{m}"' for w, m in replaced) + '）')
    if echo_note:
        note.append('（系统提示：这句话和你上一句几乎一样，可能是仿说。请换一种更简单、更具体的问法重新问一次，'
                    '并给出选项；intent 写 echo。）')
    messages.append({'role': 'user', 'content': f'学习者说：{user_text}' + ''.join('\n' + n for n in note)})
    return messages


def p3_plain_messages(context_text, history, user_text):
    """消融实验的对照组：不做任何沟通特征处理，只给通用说明。"""
    system = (f'你是编程学习助手。判断学习者这句话的意图 intent（{_INTENT_TEXT}），'
              f'并用一句话回复，给 2 到 4 个选项。\n输出格式：{{"intent": "...", "reply": "...", "options": ["..."]}}'
              f'\n{_JSON_ONLY}')
    if context_text:
        system += f'\n\n【当前学习内容】\n{context_text}'
    messages = [{'role': 'system', 'content': system}]
    for turn in history:
        messages.append({'role': 'assistant' if turn['role'] == 'bot' else 'user', 'content': turn['text']})
    messages.append({'role': 'user', 'content': user_text})
    return messages


# ── P4 学习报告 ─────────────────────────────────────────────────────

P4_SYSTEM = f"""你是特殊教育学校的教学助手，根据一名学习者的作答记录统计写学习报告。

规则：
1. 只描述数据反映出的学习情况，并给出下一步练习建议。
2. 不做诊断，不评价情绪和性格，不和其他学生比较。
3. 学习者写作 {{name}}。
4. {_JSON_ONLY}

输出格式：{{"report": "报告正文"}}"""

_AUDIENCE = {
    'teacher': '面向教师：3 到 5 句话。说明任务完成情况、提示等级的变化（是否出现提示渐褪）、'
               '在哪类知识点上用提示较多，以及下一步建议（例如哪些步骤可以减少提示）。不超过 250 字。',
    'parent': '面向家长：3 到 4 句平实的话。说孩子这段时间学了什么、哪里做得顺利、在家可以怎样鼓励。'
              '不用专业术语。不超过 200 字。',
}


def p4_messages(stats, audience):
    user = f'【读者】{_AUDIENCE[audience]}\n\n【作答记录统计】\n{_dump(stats)}\n\n请输出报告 JSON。'
    return [{'role': 'system', 'content': P4_SYSTEM}, {'role': 'user', 'content': user}]
