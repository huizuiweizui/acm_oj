"""
启蒙层关卡模板（顺序 3 关、循环 3 关）与兴趣主题包。

模板里的 {hero_name} / {goal_name} 由主题包填充：themed() 是不经大模型的确定性改造，
用于种子数据和大模型不可用时的兜底；大模型改造（P2）以模板为底，可以按兴趣改写故事、
主题甚至地图，再经 BFS 校验可解、教师审核后才给学生。

每个模板的卡槽数都等于最短解的卡片数（tests 里有断言），循环关卡另保证不用"重复"卡放不下。
"""
import copy

THEMES = {
    'train':    {'name': '火车', 'hero': '🚂', 'goal': '🏠', 'wall': '🌲', 'hero_name': '小火车', 'goal_name': '车站'},
    'dinosaur': {'name': '恐龙', 'hero': '🦕', 'goal': '🥚', 'wall': '🌋', 'hero_name': '小恐龙', 'goal_name': '恐龙蛋'},
    'space':    {'name': '太空', 'hero': '🚀', 'goal': '🌙', 'wall': '☄️', 'hero_name': '小火箭', 'goal_name': '月亮'},
    'animal':   {'name': '小动物', 'hero': '🐱', 'goal': '🐟', 'wall': '🌳', 'hero_name': '小猫', 'goal_name': '小鱼'},
    'car':      {'name': '汽车', 'hero': '🚗', 'goal': '🏁', 'wall': '🚧', 'hero_name': '小汽车', 'goal_name': '终点'},
    'ocean':    {'name': '海洋', 'hero': '🐠', 'goal': '🐚', 'wall': '🦀', 'hero_name': '小鱼', 'goal_name': '贝壳'},
    'robot':    {'name': '机器人', 'hero': '🤖', 'goal': '🔋', 'wall': '🧱', 'hero_name': '小机器人', 'goal_name': '电池'},
    'plane':    {'name': '飞机', 'hero': '✈️', 'goal': '🛬', 'wall': '⛰️', 'hero_name': '小飞机', 'goal_name': '机场'},
    'music':    {'name': '音乐', 'hero': '🎵', 'goal': '🎹', 'wall': '🔇', 'hero_name': '小音符', 'goal_name': '钢琴'},
    'ball':     {'name': '踢球', 'hero': '⚽', 'goal': '🥅', 'wall': '🧍', 'hero_name': '足球', 'goal_name': '球门'},
}
DEFAULT_THEME = 'train'

LEVELS = [
    {
        'key': 'L1', 'knowledge': 'sequence',
        'title': '向前走',
        'story': ['{hero_name}要去{goal_name}。', '一直向前走。'],
        'grid': {'w': 5, 'h': 3},
        'start': {'x': 0, 'y': 1, 'dir': 'E'},
        'goal': {'x': 3, 'y': 1},
        'walls': [],
        'cards': ['forward'],
        'slots': 3,
    },
    {
        'key': 'L2', 'knowledge': 'sequence',
        'title': '拐个弯',
        'story': ['{goal_name}在上面。', '走一走，再转弯。'],
        'grid': {'w': 4, 'h': 4},
        'start': {'x': 0, 'y': 3, 'dir': 'E'},
        'goal': {'x': 2, 'y': 1},
        'walls': [[0, 1], [1, 1]],
        'cards': ['forward', 'left', 'right'],
        'slots': 5,
    },
    {
        'key': 'L3', 'knowledge': 'sequence',
        'title': '绕过障碍',
        'story': ['前面有障碍。', '绕过去找{goal_name}。'],
        'grid': {'w': 4, 'h': 3},
        'start': {'x': 0, 'y': 0, 'dir': 'E'},
        'goal': {'x': 3, 'y': 1},
        'walls': [[2, 0]],
        'cards': ['forward', 'left', 'right'],
        'slots': 6,
    },
    {
        'key': 'L4', 'knowledge': 'loop',
        'title': '重复前进',
        'story': ['路很长。', '用重复卡走得快。'],
        'grid': {'w': 6, 'h': 3},
        'start': {'x': 0, 'y': 1, 'dir': 'E'},
        'goal': {'x': 5, 'y': 1},
        'walls': [],
        'cards': ['forward', 'repeat'],
        'slots': 2,
    },
    {
        'key': 'L5', 'knowledge': 'loop',
        'title': '长长的路',
        'story': ['{goal_name}在右上角。', '重复前进，再转弯。'],
        'grid': {'w': 5, 'h': 5},
        'start': {'x': 0, 'y': 4, 'dir': 'E'},
        'goal': {'x': 4, 'y': 0},
        'walls': [],
        'cards': ['forward', 'left', 'right', 'repeat'],
        'slots': 5,
    },
    {
        'key': 'L6', 'knowledge': 'loop',
        'title': '绕开大墙',
        'story': ['右边有一堵墙。', '先往下，再往右。'],
        'grid': {'w': 6, 'h': 5},
        'start': {'x': 0, 'y': 0, 'dir': 'E'},
        'goal': {'x': 5, 'y': 3},
        'walls': [[2, 0], [2, 1], [2, 2]],
        'cards': ['forward', 'left', 'right', 'repeat'],
        'slots': 6,
    },
]

_BY_KEY = {lv['key']: lv for lv in LEVELS}


def get_level(key):
    return _BY_KEY.get(key)


def theme_of(theme_key):
    return THEMES.get(theme_key) or THEMES[DEFAULT_THEME]


def themed(template, theme_key):
    """模板 + 主题包 → 关卡 JSON（不经大模型）。"""
    th = theme_of(theme_key)

    def fill(s):
        return s.format(hero_name=th['hero_name'], goal_name=th['goal_name'])

    return {
        'title': fill(template['title']),
        'story': [fill(s) for s in template['story']],
        'theme': {k: th[k] for k in ('name', 'hero', 'goal', 'wall')},
        'grid': copy.deepcopy(template['grid']),
        'start': copy.deepcopy(template['start']),
        'goal': copy.deepcopy(template['goal']),
        'walls': copy.deepcopy(template['walls']),
        'cards': list(template['cards']),
        'slots': template['slots'],
        'knowledge': template['knowledge'],
    }
