"""
学生端的学习流程：给学生看的任务内容、判定作答、提示、进度。

· 下发给学生的内容去掉答案和 analysis（思维链），排序题的代码行按任务 id 固定打乱——
  每次打开看到的顺序都一样（同一性），但不是正确顺序；
· 判定在后端做：关卡用 maze 模拟器（与前端动画同一套规则），选择 / 填空直接比对，
  排序题把代码行拼成完整程序交给评测机跑测试数据；
· 每种结果对应一句固定话术和一个固定图标（固定反馈），前端只负责显示。
"""
import random
import re

from ..content.problems import get_problem
from . import maze
from .llm import fill_name
from .runner import run_against_tests
from .validators import normalize_blank

FEEDBACK = {
    'correct':     {'icon': '✅', 'text': '做对了！'},
    'wrong':       {'icon': '🔁', 'text': '还不对，再试一次。'},
    'arrived':     {'icon': '🏁', 'text': '到达终点了！'},
    'wall':        {'icon': '🧱', 'text': '撞到障碍了。'},
    'out':         {'icon': '🚧', 'text': '走出地图了。'},
    'not_reached': {'icon': '📍', 'text': '还没到终点。'},
    'too_many':    {'icon': '🃏', 'text': '卡片太多，放不下。'},
    'incomplete':  {'icon': '🧩', 'text': '还有代码行没放好。'},
    'run_wrong':   {'icon': '🔁', 'text': '程序运行结果不对，再排一排。'},
}

STEP_HINT_ACTION = {1: 'text', 2: 'text', 3: 'text'}


def shuffled_order(n, seed):
    """0..n-1 的固定打乱；保证不等于原顺序（n ≥ 2 时）。"""
    idx = list(range(n))
    random.Random(seed).shuffle(idx)
    if n >= 2 and idx == list(range(n)):
        idx = idx[1:] + idx[:1]
    return idx


def _order_seed(task, step_index):
    return task.id * 100 + step_index


def student_content(task, nickname):
    c = fill_name(task.content or {}, nickname)
    if task.layer == 'enlighten':
        keep = ('title', 'story', 'theme', 'grid', 'start', 'goal', 'walls', 'cards', 'slots', 'knowledge')
        return dict({k: c.get(k) for k in keep}, kind='level', steps_total=1)

    steps = []
    for i, st in enumerate(c.get('steps') or []):
        s = {'type': st['type'], 'prompt': st['prompt'], 'knowledge': st.get('knowledge')}
        if st['type'] == 'choice':
            s['options'] = st['options']
        elif st['type'] == 'fill':
            s['code'] = normalize_blank(st['code'])
        elif st['type'] == 'order':
            lines = st['lines']
            s['lines'] = [lines[j] for j in shuffled_order(len(lines), _order_seed(task, i))]
        steps.append(s)
    return {'kind': 'steps', 'title': c.get('title'), 'intro': c.get('intro') or [],
            'theme': c.get('theme', ''), 'steps': steps, 'steps_total': len(steps)}


def steps_total(task):
    return 1 if task.layer == 'enlighten' else len((task.content or {}).get('steps') or [])


def done_steps(task):
    """已经做对过的步骤序号集合。"""
    return set(task.attempts.filter(is_correct=True).values_list('step_index', flat=True))


def hint(task, step_index, level, nickname):
    level = max(1, min(3, int(level)))
    if task.layer == 'enlighten':
        sol = maze.shortest_solution(task.content)
        return maze.hint_payload(task.content, sol or [], level)
    steps = (task.content or {}).get('steps') or []
    st = steps[step_index]
    return {'level': level, 'action': STEP_HINT_ACTION[level], 'text': fill_name(st['hints'][level - 1], nickname)}


def _squash(s):
    return re.sub(r'\s+', '', s or '')


class BadAnswer(ValueError):
    pass


def judge(task, step_index, answer):
    """
    判定一次作答。返回 (是否正确, 结果 dict, 要存进 StepAttempt.answer 的内容)。
    结果 dict 至少含 feedback；关卡另含 result / cards_used / shortest，排序题另含 passed / total。
    """
    if task.layer == 'enlighten':
        return _judge_level(task, answer)

    steps = (task.content or {}).get('steps') or []
    if not 0 <= step_index < len(steps):
        raise BadAnswer('步骤不存在')
    st = steps[step_index]

    if st['type'] == 'choice':
        choice = answer.get('choice')
        if not isinstance(choice, int) or isinstance(choice, bool):
            raise BadAnswer('请选择一个选项')
        ok = choice == st['answer']
        return ok, {'feedback': FEEDBACK['correct' if ok else 'wrong']}, {'choice': choice}

    if st['type'] == 'fill':
        text = str(answer.get('text', ''))[:50]
        ok = _squash(text) == _squash(st['answer'])
        return ok, {'feedback': FEEDBACK['correct' if ok else 'wrong']}, {'text': text}

    # order：answer['order'] 是学生排出的顺序，元素为"下发给学生的打乱后列表"里的下标
    order = answer.get('order')
    lines = st['lines']
    shown = [lines[j] for j in shuffled_order(len(lines), _order_seed(task, step_index))]
    if not isinstance(order, list) or not all(isinstance(i, int) and not isinstance(i, bool) for i in order):
        raise BadAnswer('排序结果格式不对')
    if sorted(order) != list(range(len(shown))):
        return False, {'feedback': FEEDBACK['incomplete']}, {'order': order}

    program = '\n'.join(shown[i] for i in order) + '\n'
    material = get_problem(task.template)
    if task.problem is None or material is None:
        raise BadAnswer('题目缺少测试数据')
    run = run_against_tests(task.problem, program, 'Python')
    ok = run['status'] == 'AC'
    result = {
        'feedback': FEEDBACK['correct' if ok else 'run_wrong'],
        'status': run['status'], 'passed': run['passed'], 'total': run['total'],
    }
    return ok, result, {'order': order, 'status': run['status'], 'passed': run['passed']}


def _judge_level(task, answer):
    level = task.content
    program = answer.get('program')
    if not isinstance(program, list) or not all(isinstance(c, dict) for c in program):
        raise BadAnswer('卡片程序格式不对')
    allowed = set(level.get('cards') or [])
    clean = []
    for c in program:
        if c.get('type') not in allowed:
            raise BadAnswer('用了这一关没有的卡片')
        card = {'type': c['type']}
        if c['type'] == 'repeat':
            card['times'] = maze._clamp_times(c.get('times'))
        clean.append(card)

    sol = maze.shortest_solution(level)
    shortest = len(sol) if sol else None
    if len(clean) > level.get('slots', 0):
        res = {'feedback': FEEDBACK['too_many'], 'result': 'too_many', 'cards_used': len(clean),
               'shortest': shortest}
        return False, res, {'program': clean, 'result': 'too_many', 'cards_used': len(clean), 'shortest': shortest}

    run = maze.simulate(level, clean)
    ok = run['result'] == 'arrived'
    res = {'feedback': FEEDBACK[run['result']], 'result': run['result'],
           'cards_used': len(clean), 'shortest': shortest}
    return ok, res, {'program': clean, 'result': run['result'], 'cards_used': len(clean), 'shortest': shortest}
