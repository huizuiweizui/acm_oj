"""
学生端的学习流程：给学生看的任务内容、判定作答、提示、进度。

· 下发给学生的内容去掉答案和 analysis（思维链），排序题的代码行按任务 id 固定打乱——
  每次打开看到的顺序都一样（同一性），但不是正确顺序；
· 判定在后端做：关卡用 maze 模拟器（与前端动画同一套规则），选择 / 填空直接比对，
  排序题把代码行拼成完整程序交给评测机跑测试数据，写代码题直接跑学生写的程序；
· 写代码题出错时说清楚是第几行、哪一类错（固定的中文说法），答案不对时给出第一组没通过的数据；
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
    'empty_code':  {'icon': '✏️', 'text': '还没有写代码。'},
    'code_wrong':  {'icon': '🔁', 'text': '输出的结果不对，再改一改。'},
    'code_error':  {'icon': '🐞', 'text': '程序出错了，看看是哪一行。'},
    'code_slow':   {'icon': '⏱️', 'text': '程序停不下来，看看循环。'},
}

CODE_MAX_CHARS = 4000

# Python 错误类型 → 一句固定的中文说明（字面、具体，不评价学生）
ERROR_TEXT = {
    'SyntaxError':       '这一行的写法不对。',
    'IndentationError':  '这一行的缩进不对。',
    'TabError':          '缩进里混用了 Tab 和空格。',
    'NameError':         '用到了一个还没有的名字，看看是不是拼错了。',
    'ValueError':        '把输入变成数字时出错了。',
    'TypeError':         '数字和文字不能直接一起算。',
    'ZeroDivisionError': '除数不能是 0。',
    'EOFError':          '读入的次数比输入的行数多。',
    'IndexError':        '下标超出了范围。',
}
_TB_LINE = re.compile(r'line (\d+)')

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
        elif st['type'] == 'code':
            s['starter'] = st.get('starter', '')
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

    if st['type'] == 'code':
        return _judge_code(task, answer)

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


def explain_error(error_type, line):
    text = ERROR_TEXT.get(error_type, '程序运行时出错了。')
    return f'第 {line} 行：{text}' if line else text


def _syntax_problem(code):
    """只编译不运行：语法错就不必占评测机名额。返回 None 或 (错误类型, 行号, 原始信息)。"""
    try:
        compile(code, 'main.py', 'exec')
    except SyntaxError as e:          # IndentationError、TabError 都是它的子类
        return type(e).__name__, e.lineno or 0, f'{type(e).__name__}: {e.msg}'
    except (ValueError, MemoryError, RecursionError):
        return 'SyntaxError', 0, 'SyntaxError'
    return None


def _runtime_problem(stderr):
    """从运行时的报错里取错误类型、出错行号和最后一行原文（不带文件路径）。"""
    lines = [x for x in (stderr or '').splitlines() if x.strip()]
    last = lines[-1].strip() if lines else ''
    etype = re.match(r'([A-Za-z_][\w.]*)', last)
    nums = _TB_LINE.findall(stderr or '')
    return (etype.group(1).rsplit('.', 1)[-1] if etype else ''), (int(nums[-1]) if nums else 0), last[:200]


def _judge_code(task, answer):
    code = answer.get('code')
    if not isinstance(code, str):
        raise BadAnswer('代码格式不对')
    code = code.replace('\r\n', '\n')[:CODE_MAX_CHARS]
    meaningful = [x for x in code.splitlines() if x.strip() and not x.strip().startswith('#')]
    if not meaningful:
        return False, {'feedback': FEEDBACK['empty_code']}, {'code': code, 'status': 'EMPTY'}
    if task.problem is None or get_problem(task.template) is None:
        raise BadAnswer('题目缺少测试数据')

    bad = _syntax_problem(code)
    if bad:
        etype, line, raw = bad
        result = {'feedback': FEEDBACK['code_error'], 'status': 'RE', 'passed': 0, 'total': None,
                  'error_line': line, 'error_text': explain_error(etype, line), 'error_raw': raw}
        return False, result, {'code': code, 'status': 'RE', 'passed': 0, 'error_line': line}

    run = run_against_tests(task.problem, code + '\n', 'Python', detail=True)
    st = run['status']
    stored = {'code': code, 'status': st, 'passed': run['passed']}
    result = {'status': st, 'passed': run['passed'], 'total': run['total']}
    if st == 'AC':
        return True, dict(result, feedback=FEEDBACK['correct']), stored
    if st == 'RE':
        etype, line, raw = _runtime_problem(run['error'])
        stored['error_line'] = line
        return False, dict(result, feedback=FEEDBACK['code_error'], error_line=line,
                           error_text=explain_error(etype, line), error_raw=raw), stored
    if st == 'TLE':
        return False, dict(result, feedback=FEEDBACK['code_slow']), stored
    return False, dict(result, feedback=FEEDBACK['code_wrong'], first_fail=run.get('first_fail')), stored


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
