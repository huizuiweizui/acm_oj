"""
画像模块：图形化问卷（一屏一题、图片选项）→ 引导对话（5 轮，以选项为主、允许自由输入）
→ P1 生成画像（含层级建议）→ 教师确认后生效。

问卷和引导对话都是固定脚本：对坚持同一性的学习者，每次看到的问题、顺序、选项都一样。
大模型只在最后一步出场——从答案里归纳兴趣、呈现偏好和个人词表（P1），而且只是"建议"，
教师确认后才生效。大模型不可用或输出不合格时用 rule_based_profile 兜底，流程照常走完。

题型（type）：
    single  单选（默认）              答案：'value'
    multi   多选，至少选一个           答案：['value', ...]
    scale   打分表：每行一个色块/形状/说法，每行选一档   答案：{'行 key': 档位 value}
带 other=True 的选项可以再写几个字，存在答案的 '<题 key>_other' 里。

界面偏好题（颜色、图标、形状、界面需求）不交给大模型，由 build_ui 确定性地换算成
学生端界面设置（背景、主色、按钮形状、是否给字号/换色按钮），写入画像的 ui 字段。
"""
from . import llm, prompts
from .validators import check_profile

# 打分表的两套档位
LIKE_LEVELS = [
    {'value': 5, 'icon': '😍', 'label': '很喜欢'},
    {'value': 4, 'icon': '🙂', 'label': '有点喜欢'},
    {'value': 3, 'icon': '😐', 'label': '一般'},
    {'value': 2, 'icon': '🙁', 'label': '不太喜欢'},
    {'value': 1, 'icon': '😣', 'label': '很不喜欢'},
]
NEED_LEVELS = [
    {'value': 'must', 'icon': '🙋', 'label': '很需要'},
    {'value': 'some', 'icon': '👍', 'label': '有点需要'},
    {'value': 'any', 'icon': '🤷', 'label': '都可以'},
    {'value': 'no', 'icon': '🙅', 'label': '不需要'},
]
OTHER = {'value': 'other', 'icon': '✏️', 'label': '其他（我来写）', 'other': True}

SURVEY = [
    {'key': 'companion', 'title': '谁陪我一起填？', 'options': [
        {'value': 'self', 'icon': '🙂', 'label': '我自己'},
        {'value': 'parent', 'icon': '👪', 'label': '家长'},
        {'value': 'teacher', 'icon': '🧑‍🏫', 'label': '老师'},
    ]},
    {'key': 'interest', 'title': '我最喜欢什么？', 'options': [
        {'value': 'train', 'icon': '🚂', 'label': '火车'},
        {'value': 'dinosaur', 'icon': '🦕', 'label': '恐龙'},
        {'value': 'space', 'icon': '🚀', 'label': '太空'},
        {'value': 'animal', 'icon': '🐱', 'label': '小动物'},
        {'value': 'car', 'icon': '🚗', 'label': '汽车'},
        {'value': 'ocean', 'icon': '🐠', 'label': '海洋'},
        {'value': 'robot', 'icon': '🤖', 'label': '机器人'},
        {'value': 'plane', 'icon': '✈️', 'label': '飞机'},
        {'value': 'music', 'icon': '🎵', 'label': '音乐'},
        {'value': 'ball', 'icon': '⚽', 'label': '踢球'},
    ]},
    {'key': 'learn_style', 'type': 'multi', 'title': '我学新东西的时候，更喜欢：', 'options': [
        {'value': 'image', 'icon': '🖼️', 'label': '看图片或图表'},
        {'value': 'listen', 'icon': '👂', 'label': '听别人讲'},
        {'value': 'do', 'icon': '✋', 'label': '自己动手做'},
        {'value': 'text', 'icon': '📖', 'label': '读文字说明'},
        {'value': 'watch', 'icon': '👀', 'label': '看别人做一遍，然后自己做'},
        {'value': 'repeat', 'icon': '🔁', 'label': '反复做很多遍'},
    ]},
    {'key': 'reading', 'title': '我能读多长的话？', 'options': [
        {'value': 'word', 'icon': '🔤', 'label': '几个字'},
        {'value': 'sentence', 'icon': '📄', 'label': '一句话'},
        {'value': 'paragraph', 'icon': '📚', 'label': '一段话'},
    ]},
    {'key': 'typing', 'title': '我会打字吗？', 'options': [
        {'value': 'yes', 'icon': '⌨️', 'label': '会'},
        {'value': 'little', 'icon': '✍️', 'label': '会一点'},
        {'value': 'no', 'icon': '✋', 'label': '还不会'},
    ]},
    {'key': 'operate', 'type': 'multi', 'title': '我用电脑或平板的时候，喜欢怎么操作？', 'options': [
        {'value': 'tap', 'icon': '👆', 'label': '点一下'},
        {'value': 'drag', 'icon': '🖐️', 'label': '拖来拖去'},
        {'value': 'keyboard', 'icon': '⌨️', 'label': '用键盘打字'},
        {'value': 'draw', 'icon': '✏️', 'label': '用手写或画画'},
        {'value': 'speak', 'icon': '🗣️', 'label': '说话'},
    ]},
    {'key': 'color_mix', 'title': '界面上有很多种颜色混在一起，我觉得：', 'options': [
        {'value': 'fine', 'icon': '😶', 'label': '没什么感觉'},
        {'value': 'a_bit', 'icon': '😕', 'label': '有点乱，不太舒服'},
        {'value': 'too_much', 'icon': '😖', 'label': '很乱，看不下去'},
        {'value': 'like', 'icon': '🌈', 'label': '其实我喜欢颜色多'},
    ]},
    {'key': 'bg_color', 'title': '我喜欢界面用什么颜色的背景？', 'options': [
        {'value': 'white', 'swatch': '#ffffff', 'icon': '⬜', 'label': '白色'},
        {'value': 'gray', 'swatch': '#eceef1', 'icon': '🩶', 'label': '浅灰色'},
        {'value': 'blue', 'swatch': '#e3eef8', 'icon': '🩵', 'label': '浅蓝色'},
        {'value': 'green', 'swatch': '#e5f2e3', 'icon': '💚', 'label': '浅绿色'},
        {'value': 'dark', 'swatch': '#26282c', 'icon': '⬛', 'label': '深色'},
        {'value': 'any', 'icon': '👌', 'label': '都可以'},
    ]},
    {'key': 'color_like', 'type': 'scale', 'title': '这些颜色，我喜欢吗？', 'levels': LIKE_LEVELS, 'rows': [
        {'key': 'blue', 'label': '蓝色', 'hint': '浅浅的天蓝色', 'swatch': '#a9d4f5'},
        {'key': 'green', 'label': '绿色', 'hint': '柔和的草绿色', 'swatch': '#a8d5a2'},
        {'key': 'yellow', 'label': '黄色', 'hint': '淡淡的柠檬黄', 'swatch': '#fbeea0'},
        {'key': 'orange', 'label': '橙色', 'hint': '暖暖的杏色', 'swatch': '#f8c99a'},
        {'key': 'pink', 'label': '粉色', 'hint': '柔和的樱花粉', 'swatch': '#f5c2d3'},
        {'key': 'red', 'label': '红色', 'hint': '不太鲜艳的红', 'swatch': '#d9827f'},
        {'key': 'purple', 'label': '紫色', 'hint': '浅浅的薰衣草紫', 'swatch': '#cbb7e6'},
        {'key': 'black', 'label': '黑色', 'swatch': '#26282c'},
        {'key': 'white', 'label': '白色', 'swatch': '#ffffff'},
        {'key': 'gray', 'label': '灰色', 'swatch': '#9ca3af'},
    ]},
    {'key': 'icon_style', 'title': '我更喜欢什么样的图标？', 'options': [
        {'value': 'line', 'icon': '⭕', 'label': '简单的线条图标'},
        {'value': 'filled', 'icon': '🔵', 'label': '有颜色填充的图标'},
        {'value': 'photo', 'icon': '📷', 'label': '像照片一样的写实图标'},
        dict(OTHER, label='我自己写一个喜欢的'),
    ]},
    {'key': 'shape_like', 'type': 'scale', 'title': '这些形状，我喜欢吗？', 'levels': LIKE_LEVELS, 'rows': [
        {'key': 'circle', 'label': '圆形', 'hint': '圆圆的按钮', 'shape': 'circle'},
        {'key': 'square', 'label': '方形', 'hint': '方方正正的按钮', 'shape': 'square'},
        {'key': 'rect', 'label': '长方形', 'hint': '长条形的按钮', 'shape': 'rect'},
        {'key': 'star', 'label': '星形', 'shape': 'star'},
        {'key': 'heart', 'label': '心形', 'shape': 'heart'},
        {'key': 'triangle', 'label': '三角形', 'shape': 'triangle'},
    ]},
    {'key': 'strengths', 'type': 'multi', 'title': '我觉得自己比较擅长：', 'options': [
        {'value': 'order', 'icon': '📐', 'label': '喜欢有规则和秩序'},
        {'value': 'pattern', 'icon': '🔍', 'label': '很会发现规律'},
        {'value': 'detail', 'icon': '🔬', 'label': '很注意细节'},
        {'value': 'focus', 'icon': '🎯', 'label': '能长时间专心做一件事'},
        {'value': 'logic', 'icon': '🧠', 'label': '喜欢逻辑问题'},
        {'value': 'device', 'icon': '💻', 'label': '喜欢电脑和电子设备'},
    ]},
    {'key': 'ui_needs', 'type': 'scale', 'title': '我希望界面是这样的：', 'levels': NEED_LEVELS, 'rows': [
        {'key': 'same_color', 'label': '颜色一直不变', 'icon': '🎨'},
        {'key': 'same_place', 'label': '按钮一直在同一个地方', 'icon': '📍'},
        {'key': 'font_size', 'label': '字体大小可以调', 'icon': '🔠'},
        {'key': 'clear_hint', 'label': '每一步都有清楚的提示', 'icon': '💡'},
        {'key': 'no_popup', 'label': '不要突然弹出东西', 'icon': '🚫'},
        {'key': 'retry', 'label': '可以有"再来一次"的按钮', 'icon': '🔁'},
        {'key': 'choose_color', 'label': '可以自己选喜欢的颜色', 'icon': '🖌️'},
    ]},
    {'key': 'coding', 'title': '我以前有没有学过编程？', 'options': [
        {'value': 'no', 'icon': '🆕', 'label': '从来没有学过'},
        {'value': 'little', 'icon': '🧩', 'label': '玩过一点点（拖积木块、让角色动起来）'},
        {'value': 'some', 'icon': '💻', 'label': '学过一些（写过简单的代码）'},
        {'value': 'lots', 'icon': '🏆', 'label': '学过不少，能自己写小程序'},
    ]},
    {'key': 'coding_is', 'type': 'multi', 'title': '我觉得编程是什么样的？', 'options': [
        {'value': 'puzzle', 'icon': '🧩', 'label': '像拼图，把一块一块拼起来'},
        {'value': 'checklist', 'icon': '📋', 'label': '像写步骤清单，一步一步告诉电脑做什么'},
        {'value': 'riddle', 'icon': '🔐', 'label': '像解谜题，要动脑筋想'},
        {'value': 'math', 'icon': '➗', 'label': '像做数学题，有对错'},
        {'value': 'unsure', 'icon': '❓', 'label': '不太清楚'},
        OTHER,
    ]},
    {'key': 'coding_hard', 'type': 'multi', 'title': '如果让我学编程，我觉得最难的可能是：', 'options': [
        {'value': 'abstract', 'icon': '🌫️', 'label': '理解抽象的概念（比如"变量"是什么）'},
        {'value': 'rules', 'icon': '📏', 'label': '记住很多不同的规则'},
        {'value': 'errors', 'icon': '⚠️', 'label': '看到错误信息不知道怎么办'},
        {'value': 'steps', 'icon': '🌀', 'label': '要想很多步，脑子转不过来'},
        {'value': 'unsure', 'icon': '❓', 'label': '不确定'},
        OTHER,
    ]},
    {'key': 'learn_wish', 'type': 'multi', 'title': '我希望编程学习是这样的：', 'options': [
        {'value': 'clear', 'icon': '👉', 'label': '每一步都有清楚的指示'},
        {'value': 'own_pace', 'icon': '🐢', 'label': '可以自己控制学习速度'},
        {'value': 'redo', 'icon': '🔁', 'label': '做错了可以重新来过，不扣分'},
        {'value': 'progress', 'icon': '📊', 'label': '可以看到自己已经完成了多少'},
        {'value': 'interest', 'icon': '❤️', 'label': '题目和我喜欢的东西有关'},
        {'value': 'visual', 'icon': '🖼️', 'label': '有图片或动画帮我理解'},
        {'value': 'practice', 'icon': '🏋️', 'label': '可以反复练习同一道题'},
        OTHER,
    ]},
    {'key': 'help', 'title': '如果任务对我来说太难了，我会：', 'options': [
        {'value': 'retry', 'icon': '💪', 'label': '愿意自己再试一试'},
        {'value': 'encourage', 'icon': '🤗', 'label': '需要有人鼓励一下'},
        {'value': 'hint', 'icon': '💡', 'label': '先看看提示'},
        {'value': 'ask', 'icon': '🙋', 'label': '去问老师'},
        {'value': 'rest', 'icon': '☕', 'label': '先休息一下再来'},
    ]},
    {'key': 'pace', 'title': '我喜欢一次做几件事？', 'options': [
        {'value': 'one', 'icon': '1️⃣', 'label': '一件'},
        {'value': 'few', 'icon': '🔢', 'label': '几件'},
    ]},
]
_SURVEY_BY_KEY = {q['key']: q for q in SURVEY}
OTHER_MAX = 20

FAVORITES = {
    'train': ['高铁', '地铁', '蒸汽火车'],
    'dinosaur': ['霸王龙', '三角龙', '腕龙'],
    'space': ['火箭', '月亮', '星星'],
    'animal': ['小猫', '小狗', '小兔子'],
    'car': ['警车', '消防车', '公交车'],
    'ocean': ['小鱼', '海豚', '鲸鱼'],
    'robot': ['扫地机器人', '变形金刚', '机械臂'],
    'plane': ['客机', '直升机', '战斗机'],
    'music': ['钢琴', '鼓', '唱歌'],
    'ball': ['足球', '篮球', '乒乓球'],
}

KEEP_NAME = '就叫它的名字'
DIALOGUE = [
    {'key': 'favorite', 'ask': '说到{interest}，你最喜欢哪个？'},
    {'key': 'own_word', 'ask': '你平时管它叫什么？', 'options': [KEEP_NAME]},
    {'key': 'tired', 'ask': '想休息的时候，你会说什么？', 'options': ['我累了', '休息', '不要了']},
    {'key': 'confused', 'ask': '听不懂的时候，你会说什么？', 'options': ['不懂', '再说一遍', '啊？']},
    {'key': 'call_me', 'ask': '你想让我叫你什么？'},
]
_STANDARD = {
    'tired': ('想休息', {'我累了', '休息', '不要了'}),
    'confused': ('没听懂', {'不懂', '再说一遍', '啊？'}),
}


def qtype(q):
    return q.get('type', 'single')


def option_label(qkey, value):
    for o in _SURVEY_BY_KEY.get(qkey, {}).get('options', []):
        if o['value'] == value:
            return o['label']
    return value or ''


def answer_text(q, survey):
    """一道题的答案转成一行中文：给教师看，也交给 P1。没答返回空字符串。"""
    survey = survey or {}
    v = survey.get(q['key'])
    other = (survey.get(f'{q["key"]}_other') or '').strip()
    kind = qtype(q)
    if kind == 'scale':
        if not isinstance(v, dict):
            return ''
        names = {lv['value']: lv['label'] for lv in q['levels']}
        return '；'.join(f'{r["label"]}：{names[v[r["key"]]]}' for r in q['rows'] if v.get(r['key']) in names)
    values = v if kind == 'multi' else [v]
    if not isinstance(values, list):
        return ''
    labels = []
    for o in q['options']:
        if o['value'] in values:
            labels.append(f'其他：{other}' if o.get('other') and other else o['label'])
    return '、'.join(labels)


def example_answers(**overrides):
    """一份覆盖全部题目的合法答案（每题取第一个选项 / 每行取第一档），用于种子数据和测试。"""
    ans = {}
    for q in SURVEY:
        kind = qtype(q)
        if kind == 'scale':
            ans[q['key']] = {r['key']: q['levels'][0]['value'] for r in q['rows']}
        elif kind == 'multi':
            ans[q['key']] = [q['options'][0]['value']]
        else:
            ans[q['key']] = q['options'][0]['value']
    ans.update(overrides)
    return ans


def valid_survey(answers):
    """问卷答案必须覆盖全部题目且取值合法。返回 (清洗后的答案, 错误)。"""
    answers = answers if isinstance(answers, dict) else {}
    clean = {}
    for n, q in enumerate(SURVEY, 1):
        key, kind, v = q['key'], qtype(q), answers.get(q['key'])
        if kind == 'scale':
            levels = {lv['value'] for lv in q['levels']}
            if not isinstance(v, dict):
                return None, f'第 {n} 题还没有选'
            for r in q['rows']:
                if v.get(r['key']) not in levels:
                    return None, f'第 {n} 题的"{r["label"]}"还没有选'
            clean[key] = {r['key']: v[r['key']] for r in q['rows']}
            continue
        allowed = [o['value'] for o in q['options']]
        if kind == 'multi':
            if not isinstance(v, list) or not v or any(x not in allowed for x in v):
                return None, f'第 {n} 题还没有选'
            chosen = [x for x in allowed if x in v]          # 去重并固定为题目里的顺序
        else:
            if v not in allowed:
                return None, f'第 {n} 题还没有选'
            chosen = [v]
        clean[key] = chosen if kind == 'multi' else v
        if any(o.get('other') and o['value'] in chosen for o in q['options']):
            other = str(answers.get(f'{key}_other') or '').strip()[:OTHER_MAX]
            if other:
                clean[f'{key}_other'] = other
    return clean, ''


def dialogue_question(survey, index, username=''):
    """第 index 轮引导问题（从 0 起）；全部问完返回 None。"""
    if index >= len(DIALOGUE):
        return None
    d = DIALOGUE[index]
    interest = survey.get('interest', '')
    options = list(d.get('options') or [])
    if d['key'] == 'favorite':
        options = list(FAVORITES.get(interest, []))
    elif d['key'] == 'call_me' and username:
        options = [username]
    return {
        'index': index, 'total': len(DIALOGUE), 'key': d['key'],
        'ask': d['ask'].format(interest=option_label('interest', interest)),
        'options': options,
    }


# ── 界面定制 ─────────────────────────────────────────────────────────

# 能当主色的颜色（黑、白、灰不当主色）；具体色值在前端 starUi.js 里，这里只给 key
ACCENT_KEYS = ['blue', 'green', 'yellow', 'orange', 'pink', 'red', 'purple']
BUTTON_SHAPES = {'circle': 'round', 'square': 'square', 'rect': 'soft'}
MARKS = {'circle': '●', 'square': '■', 'rect': '▬', 'star': '★', 'heart': '♥', 'triangle': '▲'}
DEFAULT_UI = {
    'bg': 'warm', 'accent': 'blue', 'button': 'soft', 'mark': '✓', 'icon_style': 'filled',
    'calm': True, 'font_adjust': False, 'color_choice': False, 'liked_colors': [],
}


def _top(scores, keys, at_least=4):
    """打分最高、且至少"有点喜欢"的那一项；并列取题目里靠前的。"""
    best = max(keys, key=lambda k: (scores.get(k, 0), -keys.index(k)), default=None)
    return best if best is not None and scores.get(best, 0) >= at_least else None


def build_ui(survey):
    """
    问卷里的界面偏好 → 学生端界面设置。纯规则、可重复：同样的答案永远得到同样的界面。
    定制只在填完问卷时决定一次，之后保持不变（符合坚持同一性）；
    学生自己调字号 / 换颜色的入口只在他们说"需要"时才出现。
    """
    s = survey or {}
    colors = s.get('color_like') if isinstance(s.get('color_like'), dict) else {}
    shapes = s.get('shape_like') if isinstance(s.get('shape_like'), dict) else {}
    needs = s.get('ui_needs') if isinstance(s.get('ui_needs'), dict) else {}

    ui = dict(DEFAULT_UI)
    bg = s.get('bg_color')
    if bg in ('white', 'gray', 'blue', 'green', 'dark'):
        ui['bg'] = bg
    ui['accent'] = _top(colors, ACCENT_KEYS) or DEFAULT_UI['accent']
    ui['liked_colors'] = [k for k in ACCENT_KEYS if colors.get(k, 0) >= 4]
    button = _top(shapes, list(BUTTON_SHAPES))
    if button:
        ui['button'] = BUTTON_SHAPES[button]
    mark = _top(shapes, list(MARKS))
    if mark:
        ui['mark'] = MARKS[mark]
    if s.get('icon_style') in ('line', 'filled', 'photo'):
        ui['icon_style'] = s['icon_style']
    ui['calm'] = s.get('color_mix') != 'like'
    ui['font_adjust'] = needs.get('font_size') in ('must', 'some')
    ui['color_choice'] = needs.get('choose_color') in ('must', 'some')
    return ui


def presentation_prefer(survey):
    """学习方式多选题 → 呈现偏好：只选了看图 → image，只选了读文字 → text，其余 → both。"""
    styles = (survey or {}).get('learn_style') or []
    if not isinstance(styles, list):
        return 'both'
    img, txt = 'image' in styles, 'text' in styles
    return 'image' if img and not txt else 'text' if txt and not img else 'both'


def _answer(intro, key):
    for row in intro or []:
        if row.get('key') == key:
            return (row.get('answer') or '').strip()
    return ''


def suggest_layer(survey):
    """规则：能读短句且会（一点）打字 → 入门层；否则 → 启蒙层。"""
    if survey.get('reading') in ('sentence', 'paragraph') and survey.get('typing') in ('yes', 'little'):
        return 'intro'
    return 'enlighten'


def rule_based_profile(survey, intro, fallback_nickname=''):
    """不经大模型的画像：问卷直接映射 + 引导对话里的说法收进个人词表。"""
    interest_label = option_label('interest', survey.get('interest'))
    favorite = _answer(intro, 'favorite')
    interests = [x for x in [interest_label, favorite] if x][:3]

    vocabulary = []
    own = _answer(intro, 'own_word')
    if own and own != KEEP_NAME and own not in (favorite, interest_label):
        vocabulary.append({'word': own[:10], 'meaning': (favorite or interest_label)[:10]})
    for key, (meaning, standard) in _STANDARD.items():
        said = _answer(intro, key)
        if said and said not in standard:
            vocabulary.append({'word': said[:10], 'meaning': meaning})

    layer = suggest_layer(survey)
    return {
        'nickname': _answer(intro, 'call_me')[:10] or fallback_nickname,
        'layer': layer,
        'layer_reason': ('能读短句、会打字，适合分步学习代码。' if layer == 'intro'
                         else '认字或打字还在起步，适合卡片闯关。'),
        'interests': interests,
        'theme_key': survey.get('interest', ''),
        'ui': build_ui(survey),
        'presentation': {
            'prefer': presentation_prefer(survey),
            'step_size': 'small' if survey.get('pace') == 'one' else 'normal',
        },
        'communication': {'pronoun_reversal': False, 'echolalia': False, 'notes': ''},
        'help_preference': survey.get('help', 'hint'),
        'vocabulary': vocabulary,
        'source': 'rule',
    }


def generate_profile(lp, *, tag=''):
    """
    生成画像建议，返回 (画像 dict, 个人词表 list, LLMCallLog 或 None)。
    大模型输出只覆盖它负责归纳的字段；昵称、主题包、帮助偏好等确定性字段始终来自问卷。
    """
    survey = lp.survey or {}
    intro = (lp.dialogue or {}).get('intro', [])
    base = rule_based_profile(survey, intro, lp.user.username)
    if not llm.is_configured():
        return _split(base) + (None,)

    names = [lp.user.username, base['nickname'], getattr(getattr(lp.user, 'profile', None), 'real_name', '')]
    survey_rows = [(q['title'], answer_text(q, survey)) for q in SURVEY]
    dialogue_rows = [(row['question'], llm.redact(row.get('answer', ''), names)) for row in intro]
    res = llm.chat_json('P1', prompts.p1_messages(survey_rows, dialogue_rows), learner=lp.user, tag=tag)
    chk = check_profile(res.data) if res.data is not None else None
    if chk is not None:
        llm.mark(res.log, chk)
    if chk is None or not chk.ok:
        base['source'] = 'rule'
        base['llm_note'] = '大模型画像未通过校验，已用规则生成'
        return _split(base) + (res.log,)

    d = res.data
    merged = dict(base)
    merged.update({
        'layer': d['layer'],
        'layer_reason': str(d.get('layer_reason', ''))[:40],
        'interests': [str(x)[:8] for x in d['interests']][:3],
        'presentation': {
            'prefer': d['presentation']['prefer'],
            'step_size': d['presentation'].get('step_size') if d['presentation'].get('step_size') in ('small', 'normal')
            else base['presentation']['step_size'],
        },
        'communication': {
            'pronoun_reversal': d['communication']['pronoun_reversal'],
            'echolalia': d['communication']['echolalia'],
            'notes': str(d['communication'].get('notes', ''))[:60],
        },
        'vocabulary': [{'word': v['word'].strip(), 'meaning': v['meaning'].strip()} for v in d['vocabulary']],
        'source': 'llm',
    })
    return _split(merged) + (res.log,)


def _split(profile):
    """个人词表单独存一列（LearnerProfile.vocabulary），不放在画像 JSON 里。"""
    p = dict(profile)
    vocab = p.pop('vocabulary', [])
    return p, vocab
