"""
4 个虚构学习者（启蒙层、入门层各 2 个，兴趣不同），用于展示"同一题目的不同改造结果"。
全部为虚构数据——演示与测试不使用任何真实学生的信息。
"""

LEARNERS = [
    {
        'username': 'star_hang', 'nickname': '小航', 'layer': 'enlighten',
        'survey': {'interest': 'train', 'view': 'image', 'reading': 'word', 'typing': 'no',
                   'coding': 'no', 'pace': 'one', 'help': 'hint', 'companion': 'parent'},
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
        'survey': {'interest': 'animal', 'view': 'image', 'reading': 'word', 'typing': 'little',
                   'coding': 'no', 'pace': 'one', 'help': 'ask', 'companion': 'teacher'},
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
        'survey': {'interest': 'dinosaur', 'view': 'text', 'reading': 'sentence', 'typing': 'yes',
                   'coding': 'little', 'pace': 'few', 'help': 'retry', 'companion': 'self'},
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
    },
    {
        'username': 'star_yu', 'nickname': '小雨', 'layer': 'intro',
        'survey': {'interest': 'space', 'view': 'both', 'reading': 'paragraph', 'typing': 'yes',
                   'coding': 'no', 'pace': 'one', 'help': 'hint', 'companion': 'parent'},
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
    },
]

TEACHER_USERNAME = 'star_teacher'
TEAM_NAME = '星语示范班'
