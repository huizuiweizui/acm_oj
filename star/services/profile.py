"""
画像模块：图形化问卷（一屏一题、图片选项）→ 引导对话（5 轮，以选项为主、允许自由输入）
→ P1 生成画像（含层级建议）→ 教师确认后生效。

问卷和引导对话都是固定脚本：对坚持同一性的学习者，每次看到的问题、顺序、选项都一样。
大模型只在最后一步出场——从答案里归纳兴趣、呈现偏好和个人词表（P1），而且只是"建议"，
教师确认后才生效。大模型不可用或输出不合格时用 rule_based_profile 兜底，流程照常走完。
"""
from . import llm, prompts
from .validators import check_profile

SURVEY = [
    {'key': 'interest', 'title': '你最喜欢什么？', 'options': [
        {'value': 'train', 'icon': '🚂', 'label': '火车'},
        {'value': 'dinosaur', 'icon': '🦕', 'label': '恐龙'},
        {'value': 'space', 'icon': '🚀', 'label': '太空'},
        {'value': 'animal', 'icon': '🐱', 'label': '小动物'},
        {'value': 'car', 'icon': '🚗', 'label': '汽车'},
        {'value': 'ocean', 'icon': '🐠', 'label': '海洋'},
    ]},
    {'key': 'view', 'title': '你喜欢看图，还是看字？', 'options': [
        {'value': 'image', 'icon': '🖼️', 'label': '看图'},
        {'value': 'text', 'icon': '📖', 'label': '看字'},
        {'value': 'both', 'icon': '👍', 'label': '都可以'},
    ]},
    {'key': 'reading', 'title': '你能读多长的话？', 'options': [
        {'value': 'word', 'icon': '🔤', 'label': '几个字'},
        {'value': 'sentence', 'icon': '📄', 'label': '一句话'},
        {'value': 'paragraph', 'icon': '📚', 'label': '一段话'},
    ]},
    {'key': 'typing', 'title': '你会打字吗？', 'options': [
        {'value': 'yes', 'icon': '⌨️', 'label': '会'},
        {'value': 'little', 'icon': '✍️', 'label': '会一点'},
        {'value': 'no', 'icon': '✋', 'label': '还不会'},
    ]},
    {'key': 'coding', 'title': '你玩过编程吗？', 'options': [
        {'value': 'yes', 'icon': '💻', 'label': '玩过'},
        {'value': 'little', 'icon': '🧩', 'label': '玩过一点'},
        {'value': 'no', 'icon': '🆕', 'label': '没玩过'},
    ]},
    {'key': 'pace', 'title': '你喜欢一次做几件事？', 'options': [
        {'value': 'one', 'icon': '1️⃣', 'label': '一件'},
        {'value': 'few', 'icon': '🔢', 'label': '几件'},
    ]},
    {'key': 'help', 'title': '不会的时候，你想怎么办？', 'options': [
        {'value': 'hint', 'icon': '💡', 'label': '看提示'},
        {'value': 'ask', 'icon': '🙋', 'label': '问老师'},
        {'value': 'retry', 'icon': '🔁', 'label': '自己再试'},
    ]},
    {'key': 'companion', 'title': '谁陪你一起填？', 'options': [
        {'value': 'self', 'icon': '🙂', 'label': '我自己'},
        {'value': 'parent', 'icon': '👪', 'label': '家长'},
        {'value': 'teacher', 'icon': '🧑‍🏫', 'label': '老师'},
    ]},
]
_SURVEY_BY_KEY = {q['key']: q for q in SURVEY}

FAVORITES = {
    'train': ['高铁', '地铁', '蒸汽火车'],
    'dinosaur': ['霸王龙', '三角龙', '腕龙'],
    'space': ['火箭', '月亮', '星星'],
    'animal': ['小猫', '小狗', '小兔子'],
    'car': ['警车', '消防车', '公交车'],
    'ocean': ['小鱼', '海豚', '鲸鱼'],
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


def option_label(qkey, value):
    for o in _SURVEY_BY_KEY.get(qkey, {}).get('options', []):
        if o['value'] == value:
            return o['label']
    return value or ''


def valid_survey(answers):
    """问卷答案必须覆盖全部题目且取值合法。返回 (清洗后的答案, 错误)。"""
    clean = {}
    for q in SURVEY:
        v = (answers or {}).get(q['key'])
        if v not in {o['value'] for o in q['options']}:
            return None, f'第 {SURVEY.index(q) + 1} 题还没有选'
        clean[q['key']] = v
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
        'presentation': {
            'prefer': survey.get('view', 'both'),
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
    survey_rows = [(q['title'], option_label(q['key'], survey.get(q['key']))) for q in SURVEY]
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
