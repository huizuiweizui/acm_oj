"""
用平台评测机跑一段程序，只要一个对错。

两处用到：
  · 入门层"排序题"——学生排好的代码行拼成完整程序，跑原题测试数据判定。用运行结果而不是
    逐行比对，是因为有些行交换顺序后程序依然正确（比如两行互不依赖的读入），运行验证
    可以接受所有等价的正确答案；
  · 改造链校验——确认参考解本身能通过测试数据（"评测机验证代码正确"）。

和正式评测（judge.services.judger）的区别：不建 Submission、不计 AC / Rating。
执行照样经过 sandbox（生产环境是 Docker 隔离），并占用"自定义运行"那组并发名额，
抢不走比赛评测的 worker。名额等不到时抛 RunQueueBusy，由视图回 503。
"""
import hashlib
import shutil
import tempfile

from django.core.cache import cache

from judge.services.judge_queue import run_slot
from judge.services.judger import _normalize
from judge.services.sandbox import compile_code, run_code, source_path


def run_against_tests(problem, code, language='Python', detail=False):
    """
    返回 {'status': 'AC'|'WA'|'RE'|'TLE'|'MLE'|'OLE'|'CE'|'NT', 'passed': k, 'total': n, 'error': str}
    status 为第一个未通过测试点的结果；全部通过才是 AC。

    detail=True 时（学生自己写的程序）另带 'first_fail': {'input', 'expected', 'output'}——
    第一个没通过的测试点，各截取前 200 个字符，让学生看到具体是哪组数据错了。
    星语入门题的测试数据本来就很简单，不算泄题。
    """
    cases = list(problem.test_cases.all().order_by('sort_order'))
    if not cases:
        return {'status': 'NT', 'passed': 0, 'total': 0, 'error': '该题没有测试数据'}

    tmp_dir = tempfile.mkdtemp(prefix='star_')
    try:
        with open(source_path(language, tmp_dir), 'w', encoding='utf-8') as f:
            f.write(code)
        with run_slot():
            ok, err = compile_code(language, tmp_dir)
            if not ok:
                return {'status': 'CE', 'passed': 0, 'total': len(cases), 'error': err[:500]}

            status, passed, first_error, first_fail = 'AC', 0, '', None
            for tc in cases:
                rc, out, stderr, timed_out, exceeded = run_code(
                    language, tmp_dir, tc.input_data,
                    problem.time_limit / 1000.0, problem.memory_limit,
                )
                if timed_out:
                    s = 'TLE'
                elif rc == 137:
                    s = 'MLE'
                elif exceeded:
                    s = 'OLE'
                elif rc != 0:
                    s = 'RE'
                else:
                    s = 'AC' if _normalize(out) == _normalize(tc.expected_output) else 'WA'
                if s == 'AC':
                    passed += 1
                elif status == 'AC':
                    status, first_error = s, (stderr or '')[:500]
                    first_fail = {'input': tc.input_data[:200], 'expected': tc.expected_output[:200],
                                  'output': (out or '')[:200]}
        res = {'status': status, 'passed': passed, 'total': len(cases), 'error': first_error}
        if detail:
            res['first_fail'] = first_fail
        return res
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def reference_passes(problem, code, language='Python'):
    """参考解能否通过测试数据。结果缓存 10 分钟——同一道题连续改造多次时不必反复跑。"""
    digest = hashlib.sha1(f'{problem.id}\n{language}\n{code}'.encode('utf-8')).hexdigest()
    key = f'star:ref:{digest}'
    hit = cache.get(key)
    if hit is not None:
        return hit
    ok = run_against_tests(problem, code, language)['status'] == 'AC'
    cache.set(key, ok, 600)
    return ok
