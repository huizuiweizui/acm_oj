"""
指令卡片闯关的规则核心：模拟器 + 最短解搜索 + 三级提示。

前端 frontend/src/components/star/maze.js 是这里的逐行翻译，两边规则必须一致——
同一份用例 star/tests/maze_cases.json 同时喂给 Django 测试和 node 校验脚本。

坐标：x 向右、y 向下，(0, 0) 在左上角。朝向 N / E / S / W。

卡片（程序是卡片列表，每张卡片是 {'type': ...}）：
    forward  前进一格
    left     原地左转
    right    原地右转
    repeat   重复 N 次（{'type': 'repeat', 'times': N}，N 取 2–5），
             作用于紧随其后的那一张基础卡片（前进 / 左转 / 右转）。
             后面没有基础卡片（在末尾，或后面又是一张重复卡）时，这张重复卡不起作用。

    "重复卡只管下一张"是刻意的简化：启蒙层先建立"同一件事做很多次"的概念，
    不引入嵌套的循环体。它同时让程序保持线性——每张卡片都只是状态图上的一条边，
    所以最少卡片数可以在 (x, y, 朝向) 状态图上用最短路精确求出，不必搜索程序空间。

执行结果（result）：
    arrived      踏上终点即成功并立刻停止，后面多余的卡片不再执行
    wall         撞墙，停在原地
    out          走出地图，停在原地
    not_reached  卡片执行完了还没到终点
"""
import heapq

DIRS = ['N', 'E', 'S', 'W']
DELTA = {'N': (0, -1), 'E': (1, 0), 'S': (0, 1), 'W': (-1, 0)}
BASIC = ('forward', 'left', 'right')
CARD_TYPES = BASIC + ('repeat',)
REPEAT_MIN, REPEAT_MAX = 2, 5
# 原子动作上限：卡片数有卡槽限制、重复最多 5 次，正常程序远到不了这里，只防构造的异常输入
MAX_ACTIONS = 200


def _turn(d, kind):
    i = DIRS.index(d)
    return DIRS[(i + 3) % 4] if kind == 'left' else DIRS[(i + 1) % 4]


def _clamp_times(times):
    try:
        n = int(times)
    except (TypeError, ValueError):
        n = REPEAT_MIN
    return max(REPEAT_MIN, min(REPEAT_MAX, n))


def simulate(level, program):
    """
    执行一段程序。返回：
        {
          'result': 'arrived' | 'wall' | 'out' | 'not_reached',
          'frames': [{'x', 'y', 'dir', 'card', 'rep'}...],   # 第一帧是起点（card=-1）
          'cards_used': 程序的卡片张数,
        }
    每个原子动作产生一帧；card 是正在执行的基础卡片下标，rep 是重复卡的第几次（从 1 起，
    没有重复时为 0）。撞墙 / 出界时最后一帧停在原地，card 指向出错的那张卡片。
    """
    w, h = level['grid']['w'], level['grid']['h']
    walls = {(int(c[0]), int(c[1])) for c in level.get('walls') or []}
    goal = (level['goal']['x'], level['goal']['y'])
    x, y, d = level['start']['x'], level['start']['y'], level['start']['dir']
    frames = [{'x': x, 'y': y, 'dir': d, 'card': -1, 'rep': 0}]
    actions = 0

    def act(kind, idx, rep):
        nonlocal x, y, d
        if kind in ('left', 'right'):
            d = _turn(d, kind)
        else:
            dx, dy = DELTA[d]
            nx, ny = x + dx, y + dy
            if not (0 <= nx < w and 0 <= ny < h):
                frames.append({'x': x, 'y': y, 'dir': d, 'card': idx, 'rep': rep})
                return 'out'
            if (nx, ny) in walls:
                frames.append({'x': x, 'y': y, 'dir': d, 'card': idx, 'rep': rep})
                return 'wall'
            x, y = nx, ny
        frames.append({'x': x, 'y': y, 'dir': d, 'card': idx, 'rep': rep})
        return 'arrived' if (x, y) == goal else None

    def finish(result):
        return {'result': result, 'frames': frames, 'cards_used': len(program)}

    i = 0
    while i < len(program):
        kind = (program[i] or {}).get('type')
        if kind == 'repeat':
            nxt = program[i + 1] if i + 1 < len(program) else None
            if nxt and nxt.get('type') in BASIC:
                for rep in range(1, _clamp_times(program[i].get('times')) + 1):
                    actions += 1
                    if actions > MAX_ACTIONS:
                        return finish('not_reached')
                    r = act(nxt['type'], i + 1, rep)
                    if r:
                        return finish(r)
                i += 2
                continue
            i += 1          # 悬空的重复卡：不起作用
            continue
        if kind in BASIC:
            actions += 1
            if actions > MAX_ACTIONS:
                return finish('not_reached')
            r = act(kind, i, 0)
            if r:
                return finish(r)
        i += 1
    return finish('not_reached')


def _moves(level):
    """可用的"边"：(卡片序列, 卡片数)。展开顺序固定，保证平局时总选同一条解。"""
    allowed = set(level.get('cards') or [])
    moves = []
    for kind in BASIC:
        if kind in allowed:
            moves.append(([{'type': kind}], 1))
    # 重复左转 / 右转不会比基础卡更省（转两次 = 两张卡，转三次 = 反方向一次），只展开"重复 + 前进"
    if 'repeat' in allowed and 'forward' in allowed:
        for n in range(REPEAT_MIN, REPEAT_MAX + 1):
            moves.append(([{'type': 'repeat', 'times': n}, {'type': 'forward'}], 2))
    return moves


def shortest_solution(level):
    """
    最少卡片的通关程序（list[card]），无解返回 None。

    状态 = (x, y, 朝向)，边权 = 这条边用掉的卡片数（基础卡 1，重复卡 + 前进 2），
    在状态图上跑 Dijkstra。踏上终点的那条边直接连到一个虚拟的"终点"节点，
    这和模拟器"踏上终点立即停止"的规则一致。

    平局时按 (卡片数, 入堆次序) 出堆，展开顺序固定（前进 < 左转 < 右转 < 重复），
    同一关卡每次都算出同一条示范解——提示内容因此也固定不变。
    """
    start = (level['start']['x'], level['start']['y'], level['start']['dir'])
    moves = _moves(level)
    goal_node = ('GOAL',)

    dist = {start: 0}
    parent = {}
    heap = [(0, 0, start)]
    counter = 1
    while heap:
        cost, _, state = heapq.heappop(heap)
        if state == goal_node:
            break
        if cost > dist.get(state, float('inf')):
            continue
        sub = dict(level, start={'x': state[0], 'y': state[1], 'dir': state[2]})
        for cards, weight in moves:
            run = simulate(sub, cards)
            if run['result'] in ('wall', 'out'):
                continue
            last = run['frames'][-1]
            nxt = goal_node if run['result'] == 'arrived' else (last['x'], last['y'], last['dir'])
            if nxt == state:
                continue
            new_cost = cost + weight
            if new_cost < dist.get(nxt, float('inf')):
                dist[nxt] = new_cost
                parent[nxt] = (state, cards)
                heapq.heappush(heap, (new_cost, counter, nxt))
                counter += 1

    if goal_node not in parent:
        return None
    program = []
    node = goal_node
    while node != start:
        prev, cards = parent[node]
        program[:0] = cards
        node = prev
    return program


def uses_repeat(program):
    return any(c.get('type') == 'repeat' for c in program or [])


def hint_payload(level, solution, hint_level):
    """
    三级提示（由少到多，逐级给出）：
        1 高亮下一张应该用的卡片
        2 代为放置前半段
        3 完整示范
    返回给前端的数据里带上示范解，具体"哪一张该亮"由前端对照学生当前的卡槽算出。
    """
    half = (len(solution) + 1) // 2
    # 不把"重复卡"和它管的那张卡片拆开
    if half and solution[half - 1].get('type') == 'repeat':
        half += 1
    texts = {
        1: '看亮起来的卡片。',
        2: '前一半已经放好了。',
        3: '看一遍完整的走法。',
    }
    actions = {1: 'highlight', 2: 'place', 3: 'demo'}
    return {
        'level': hint_level,
        'text': texts[hint_level],
        'action': actions[hint_level],
        'solution': solution,
        'place_count': half,
    }
