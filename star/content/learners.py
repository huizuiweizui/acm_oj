"""
40 个虚构学习者（启蒙层、入门层各 20 个），用于展示"同一题目的不同改造结果"，
也让教师端的学生列表、按团队布置和统计页有足够的人数可看。

前 4 个是手写的完整样例（SHOWCASE，录屏和 star_pregen 默认用它们）；
其余 36 个由 _EXTRA 每行一条展开，兴趣覆盖全部 10 个主题，沟通特点和界面偏好各不相同。
全部为虚构数据——演示与测试不使用任何真实学生的信息。
"""
from star.content.levels import THEMES

LEARNERS = [
    {
        'username': 'star_hang', 'nickname': '小航', 'layer': 'enlighten',
        'survey': {'interest': 'train', 'learn_style': ['image', 'repeat'], 'reading': 'word', 'typing': 'no',
                   'coding': 'no', 'pace': 'one', 'help': 'hint', 'companion': 'parent',
                   # 界面偏好：浅蓝背景、喜欢绿色、圆形按钮，需要能调字号
                   'bg_color': 'blue', 'color_mix': 'too_much',
                   'color_like': {'green': 5, 'blue': 4, 'red': 1},
                   'shape_like': {'circle': 5, 'star': 4},
                   'ui_needs': {'font_size': 'must', 'same_place': 'must'}},
        'intro': [
            ('favorite', '说到火车，你最喜欢哪个？', '高铁'),
            ('own_word', '你平时管它叫什么？', '呜呜'),
            ('tired', '想休息的时候，你会说什么？', '停停'),
            ('confused', '听不懂的时候，你会说什么？', '听不懂的时候'),
            ('call_me', '你想让我叫你什么？', '小航'),
        ],
        'profile': {
            'interests': ['火车', '高铁'], 'theme_key': 'train',
            'presentation': {'prefer': 'image', 'step_size': 'small'},
            'communication': {'pronoun_reversal': True, 'echolalia': True,
                              'notes': '会用"你"指自己；有时重复问题的后半句。'},
            'layer_reason': '认字较少、还不会打字，适合卡片闯关。',
        },
        'vocabulary': [{'word': '呜呜', 'meaning': '火车'}, {'word': '停停', 'meaning': '想休息'}],
    },
    {
        'username': 'star_duo', 'nickname': '朵朵', 'layer': 'enlighten',
        'survey': {'interest': 'animal', 'learn_style': ['image', 'watch'], 'reading': 'word', 'typing': 'little',
                   'coding': 'no', 'pace': 'one', 'help': 'ask', 'companion': 'teacher',
                   # 界面偏好：白色背景、喜欢粉色、心形标记，想自己选颜色
                   'bg_color': 'white', 'color_mix': 'a_bit',
                   'color_like': {'pink': 5, 'purple': 4},
                   'shape_like': {'heart': 5, 'circle': 4},
                   'ui_needs': {'choose_color': 'must'}},
        'intro': [
            ('favorite', '说到小动物，你最喜欢哪个？', '小猫'),
            ('own_word', '你平时管它叫什么？', '喵喵'),
            ('tired', '想休息的时候，你会说什么？', '休息'),
            ('confused', '听不懂的时候，你会说什么？', '啊？'),
            ('call_me', '你想让我叫你什么？', '朵朵'),
        ],
        'profile': {
            'interests': ['小动物', '小猫'], 'theme_key': 'animal',
            'presentation': {'prefer': 'image', 'step_size': 'small'},
            'communication': {'pronoun_reversal': False, 'echolalia': True, 'notes': ''},
            'layer_reason': '能认少量字，喜欢看图，适合卡片闯关。',
        },
        'vocabulary': [{'word': '喵喵', 'meaning': '小猫'}],
    },
    {
        'username': 'star_jie', 'nickname': '阿杰', 'layer': 'intro',
        'survey': {'interest': 'dinosaur', 'learn_style': ['text', 'do'], 'reading': 'sentence', 'typing': 'yes',
                   'coding': 'little', 'pace': 'few', 'help': 'retry', 'companion': 'self',
                   # 界面偏好：浅绿背景、喜欢橙色、方形按钮
                   'bg_color': 'green', 'color_mix': 'fine',
                   'color_like': {'orange': 5, 'green': 4},
                   'shape_like': {'square': 5},
                   'ui_needs': {}},
        'intro': [
            ('favorite', '说到恐龙，你最喜欢哪个？', '腕龙'),
            ('own_word', '你平时管它叫什么？', '大长脖'),
            ('tired', '想休息的时候，你会说什么？', '我累了'),
            ('confused', '听不懂的时候，你会说什么？', '再说一遍'),
            ('call_me', '你想让我叫你什么？', '阿杰'),
        ],
        'profile': {
            'interests': ['恐龙', '腕龙'], 'theme_key': 'dinosaur',
            'presentation': {'prefer': 'text', 'step_size': 'normal'},
            'communication': {'pronoun_reversal': False, 'echolalia': False, 'notes': ''},
            'layer_reason': '能读短句、会打字，适合分步学习代码。',
        },
        'vocabulary': [{'word': '大长脖', 'meaning': '腕龙'}],
        # 表达记忆：(说法, 意思, 状态, 大模型一致次数, 直接命中次数)；说法是词表替换之后的文本
        'expressions': [('我要看一下', 'ask_hint', 'confirmed', 2, 4), ('脑子转不动了', 'dont_know', 'auto', 2, 1),
                        ('腕龙走得好慢', 'chat', 'auto', 1, 0)],
    },
    {
        'username': 'star_yu', 'nickname': '小雨', 'layer': 'intro',
        'survey': {'interest': 'space', 'learn_style': ['image', 'text'], 'reading': 'paragraph', 'typing': 'yes',
                   'coding': 'no', 'pace': 'one', 'help': 'hint', 'companion': 'parent',
                   # 界面偏好：深色背景、喜欢紫色、星形标记、长方形按钮
                   'bg_color': 'dark', 'color_mix': 'a_bit',
                   'color_like': {'purple': 5, 'blue': 5, 'black': 5},
                   'shape_like': {'star': 5, 'rect': 4},
                   'ui_needs': {'font_size': 'some'}},
        'intro': [
            ('favorite', '说到太空，你最喜欢哪个？', '火箭'),
            ('own_word', '你平时管它叫什么？', '飞飞'),
            ('tired', '想休息的时候，你会说什么？', '不要了'),
            ('confused', '听不懂的时候，你会说什么？', '你不懂'),
            ('call_me', '你想让我叫你什么？', '小雨'),
        ],
        'profile': {
            'interests': ['太空', '火箭'], 'theme_key': 'space',
            'presentation': {'prefer': 'both', 'step_size': 'small'},
            'communication': {'pronoun_reversal': True, 'echolalia': False,
                              'notes': '说"你不懂"时指的是自己没听懂。'},
            'layer_reason': '能读一段话、会打字，适合分步学习代码。',
        },
        'vocabulary': [{'word': '飞飞', 'meaning': '火箭'}, {'word': '你不懂', 'meaning': '我没听懂'}],
        'expressions': [('我没听懂', 'dont_know', 'confirmed', 0, 3), ('下一个下一个', 'skip', 'auto', 2, 1)],
    },
]

SHOWCASE = [s['username'] for s in LEARNERS]

# 用户名, 昵称, 层级, 兴趣, 最喜欢的, 自己的叫法, 想休息时说, 听不懂时说, 代词逆转, 仿说, 背景色, 喜欢的颜色, 喜欢的形状
# 代词逆转的学生"听不懂时说"里带"你"，指的是自己——词表里会记一条"你→我"的解释。
_EXTRA = [
    ('star_tao', '桃桃', 'enlighten', 'ocean', '小丑鱼', '橙橙', '休息', '啊？', False, True, 'blue', ('orange', 'blue'), ('circle',)),
    ('star_le', '乐乐', 'enlighten', 'car', '消防车', '嘀嘟', '停车', '你不会', True, False, 'white', ('red', 'yellow'), ('square', 'circle')),
    ('star_niu', '牛牛', 'enlighten', 'ball', '足球', '圆圆', '不踢了', '不懂', False, False, 'green', ('green', 'white'), ('circle',)),
    ('star_mi', '米粒', 'enlighten', 'animal', '小狗', '汪汪', '睡觉', '啊？', False, True, 'gray', ('yellow', 'orange'), ('heart', 'circle')),
    ('star_xing', '星星', 'enlighten', 'space', '月亮', '弯弯', '不要了', '你听不懂', True, True, 'dark', ('blue', 'purple'), ('star',)),
    ('star_kai', '凯凯', 'enlighten', 'robot', '扫地机', '嘟嘟', '关机', '再说一遍', False, False, 'gray', ('gray', 'blue'), ('square', 'rect')),
    ('star_bei', '贝贝', 'enlighten', 'music', '钢琴', '叮咚', '安静', '不懂', False, True, 'white', ('pink', 'white'), ('heart',)),
    ('star_feng', '小枫', 'enlighten', 'plane', '直升机', '转转', '降落', '你不知道', True, False, 'blue', ('blue', 'white'), ('triangle', 'circle')),
    ('star_dou', '豆豆', 'enlighten', 'train', '地铁', '轰轰', '到站了', '啊？', False, True, 'any', ('green', 'yellow'), ('rect',)),
    ('star_tuan', '团团', 'enlighten', 'dinosaur', '霸王龙', '嗷呜', '我累了', '不懂', False, False, 'green', ('green', 'orange'), ('triangle',)),
    ('star_ning', '宁宁', 'enlighten', 'ocean', '鲸鱼', '大鱼', '休息', '再说一遍', False, False, 'blue', ('blue', 'green'), ('circle', 'heart')),
    ('star_qiu', '球球', 'enlighten', 'ball', '篮球', '拍拍', '不玩了', '你不会', True, True, 'white', ('orange', 'red'), ('circle',)),
    ('star_xi', '小溪', 'enlighten', 'animal', '兔子', '跳跳', '休息', '啊？', False, False, 'gray', ('pink', 'white'), ('heart', 'star')),
    ('star_an', '安安', 'enlighten', 'car', '挖掘机', '大铲子', '停停', '不懂', False, True, 'any', ('yellow', 'orange'), ('square',)),
    ('star_you', '悠悠', 'enlighten', 'music', '小鼓', '咚咚', '不要了', '你听不懂', True, False, 'white', ('purple', 'pink'), ('star', 'circle')),
    ('star_chen', '晨晨', 'enlighten', 'train', '绿皮火车', '哐哐', '我累了', '再说一遍', False, False, 'green', ('green', 'gray'), ('rect', 'square')),
    ('star_ming', '明明', 'enlighten', 'space', '星星', '闪闪', '睡觉', '啊？', False, True, 'dark', ('yellow', 'black'), ('star',)),
    ('star_ke', '可可', 'enlighten', 'robot', '变形金刚', '大铁人', '休息', '你不懂', True, True, 'gray', ('red', 'blue'), ('square', 'triangle')),
    ('star_hao', '浩浩', 'intro', 'plane', '大客机', '大飞机', '我累了', '再说一遍', False, False, 'blue', ('blue', 'white'), ('rect',)),
    ('star_lin', '小林', 'intro', 'dinosaur', '三角龙', '三只角', '休息一下', '不懂', False, False, 'green', ('green', 'orange'), ('triangle', 'square')),
    ('star_rui', '瑞瑞', 'intro', 'robot', '机械臂', '铁手', '不要了', '你不明白', True, False, 'dark', ('gray', 'blue'), ('square',)),
    ('star_jia', '佳佳', 'intro', 'ocean', '海豚', '蓝蓝', '休息', '再说一遍', False, True, 'blue', ('blue', 'purple'), ('circle', 'heart')),
    ('star_zhe', '哲哲', 'intro', 'space', '空间站', '太空房子', '我累了', '不懂', False, False, 'dark', ('black', 'blue'), ('rect', 'star')),
    ('star_yi', '一一', 'intro', 'music', '小提琴', '吱吱', '安静一下', '啊？', False, False, 'white', ('purple', 'white'), ('circle',)),
    ('star_tong', '童童', 'intro', 'car', '赛车', '快快', '停一下', '你不会', True, True, 'gray', ('red', 'black'), ('triangle',)),
    ('star_xuan', '轩轩', 'intro', 'train', '动车', '白龙', '休息', '再说一遍', False, False, 'white', ('white', 'blue'), ('rect', 'square')),
    ('star_qi', '琪琪', 'intro', 'animal', '熊猫', '黑白熊', '我累了', '不懂', False, True, 'green', ('green', 'pink'), ('heart',)),
    ('star_bo', '博博', 'intro', 'ball', '守门员', '大手套', '不踢了', '再说一遍', False, False, 'any', ('orange', 'green'), ('circle', 'square')),
    ('star_yang', '阳阳', 'intro', 'dinosaur', '翼龙', '飞龙', '不要了', '你不知道', True, False, 'gray', ('orange', 'yellow'), ('triangle', 'star')),
    ('star_shan', '珊珊', 'intro', 'ocean', '章鱼', '八只脚', '休息', '啊？', False, False, 'blue', ('pink', 'blue'), ('heart', 'circle')),
    ('star_cheng', '橙子', 'intro', 'space', '土星', '带圈星', '我累了', '不懂', False, False, 'dark', ('orange', 'purple'), ('circle', 'star')),
    ('star_hui', '晖晖', 'intro', 'robot', '编程小车', '小方块', '关机', '你不明白', True, True, 'white', ('blue', 'green'), ('square',)),
    ('star_yan', '小燕', 'intro', 'plane', '滑翔机', '大鸟', '降落', '再说一遍', False, False, 'blue', ('white', 'gray'), ('triangle',)),
    ('star_kang', '康康', 'intro', 'car', '公交车', '大巴巴', '到站了', '不懂', False, True, 'green', ('yellow', 'green'), ('rect',)),
    ('star_ruo', '若若', 'intro', 'music', '吉他', '弹弹', '休息一下', '啊？', False, False, 'any', ('purple', 'pink'), ('star', 'heart')),
    ('star_shu', '舒舒', 'intro', 'animal', '小鸟', '啾啾', '我累了', '你听不懂', True, False, 'white', ('yellow', 'blue'), ('circle', 'heart')),
]

# 按序号轮换的问卷题——让同一层的学生在学习方式、求助方式、陪同者、界面需求上也各不相同
_STYLES = {
    'enlighten': [['image', 'repeat'], ['image', 'watch'], ['image', 'do'], ['watch', 'listen'], ['image', 'listen']],
    'intro': [['text', 'do'], ['image', 'text'], ['do', 'repeat'], ['text', 'watch'], ['image', 'do']],
}
_READING = {'enlighten': ['word', 'word', 'sentence'], 'intro': ['sentence', 'paragraph']}
_TYPING = {'enlighten': ['no', 'little', 'no'], 'intro': ['yes', 'yes', 'little']}
_CODING = {'enlighten': ['no', 'no', 'little'], 'intro': ['little', 'no', 'some', 'little']}
_PACE = {'enlighten': ['one'], 'intro': ['few', 'one', 'few']}
_HELP = ['hint', 'ask', 'retry', 'encourage', 'rest']
_COMPANION = ['parent', 'teacher', 'self', 'parent']
_COLOR_MIX = ['a_bit', 'too_much', 'fine', 'a_bit', 'like']
_UI_NEEDS = [
    {'same_place': 'must', 'no_popup': 'must'},
    {'font_size': 'must'},
    {'clear_hint': 'must', 'retry': 'some'},
    {'choose_color': 'must', 'same_color': 'some'},
    {},
]
_READ_TEXT = {'word': '认字较少', 'sentence': '能读短句', 'paragraph': '能读一段话'}
_TYPE_TEXT = {'no': '还不会打字', 'little': '会打一点字', 'yes': '会打字'}
_LAYER_TEXT = {'enlighten': '适合卡片闯关', 'intro': '适合分步学习代码'}


def _pick(seq, i):
    return seq[i % len(seq)]


def _expand(i, row):
    (username, nickname, layer, interest, favorite, own_word, tired, confused,
     pronoun, echo, bg, colors, shapes) = row
    survey = {
        'interest': interest, 'learn_style': _pick(_STYLES[layer], i),
        'reading': _pick(_READING[layer], i), 'typing': _pick(_TYPING[layer], i),
        'coding': _pick(_CODING[layer], i), 'pace': _pick(_PACE[layer], i),
        'help': _pick(_HELP, i), 'companion': _pick(_COMPANION, i),
        'bg_color': bg, 'color_mix': _pick(_COLOR_MIX, i),
        'color_like': dict(zip(colors, (5, 4))), 'shape_like': dict(zip(shapes, (5, 4))),
        'ui_needs': _pick(_UI_NEEDS, i),
    }
    styles = survey['learn_style']
    img, txt = 'image' in styles, 'text' in styles
    notes = []
    if pronoun:
        notes.append(f'会用"你"指自己，说"{confused}"是自己不明白。')
    if echo:
        notes.append('有时重复问题的后半句。')
    vocabulary = [{'word': own_word, 'meaning': favorite}]
    if pronoun:
        vocabulary.append({'word': confused, 'meaning': confused.replace('你', '我', 1)})
    theme = THEMES[interest]['name']
    return {
        'username': username, 'nickname': nickname, 'layer': layer, 'survey': survey,
        'intro': [
            ('favorite', f'说到{theme}，你最喜欢哪个？', favorite),
            ('own_word', '你平时管它叫什么？', own_word),
            ('tired', '想休息的时候，你会说什么？', tired),
            ('confused', '听不懂的时候，你会说什么？', confused),
            ('call_me', '你想让我叫你什么？', nickname),
        ],
        'profile': {
            'interests': [theme, favorite], 'theme_key': interest,
            'presentation': {'prefer': 'image' if img and not txt else 'text' if txt and not img else 'both',
                             'step_size': 'small' if survey['pace'] == 'one' else 'normal'},
            'communication': {'pronoun_reversal': pronoun, 'echolalia': echo, 'notes': ''.join(notes)},
            'layer_reason': f'{_READ_TEXT[survey["reading"]]}、{_TYPE_TEXT[survey["typing"]]}，{_LAYER_TEXT[layer]}。',
        },
        'vocabulary': vocabulary,
    }


LEARNERS += [_expand(i, row) for i, row in enumerate(_EXTRA)]

TEACHER_USERNAME = 'star_teacher'
TEAM_NAME = '星语示范班'
