import os
import subprocess
import tempfile

from django.db.models import F

from ..models import ContestParticipant, Problem, Submission, UserProfile
from .ai_feedback import (
    _ai_call, _ai_suggest_prompt, _ai_verdict_prompt, _async_ai_feedback,
)
from .rating import _update_rating


def judge_submission(submission, problem):
    """
    评测引擎 — 对应技术方案书 §8.2
    简化方案：子进程 + timeout 命令
    依次编译→运行每个测试点→对比输出
    """
    test_cases = problem.test_cases.all().order_by('sort_order')
    if not test_cases.exists():
        # 无测试点：交由 AI 评判
        ai_text = _ai_call(_ai_verdict_prompt(submission, problem))
        if ai_text:
            first_line = ai_text.strip().split('\n')[0].strip().upper()
            verdict = first_line if first_line in ('AC', 'WA') else 'AC'
        else:
            verdict, ai_text = 'AC', ''
        submission.status = verdict
        submission.ai_feedback = ai_text
        submission.save(update_fields=['status', 'ai_feedback'])

        if verdict == 'AC':
            already_ac = Submission.objects.filter(
                user=submission.user, problem=problem, status='AC'
            ).exclude(id=submission.id).exists()
            if not already_ac:
                Problem.objects.filter(id=problem.id).update(ac_count=F('ac_count') + 1)
                UserProfile.objects.filter(user=submission.user).update(ac_count=F('ac_count') + 1)
                _update_rating(submission.user, problem)

        return {'status': verdict, 'ai_feedback': ai_text}

    # 创建临时目录
    tmp_dir = tempfile.mkdtemp(prefix='judge_')
    lang = submission.language
    code = submission.code

    COMPILE_CMD = {
        'C': 'gcc -O2 -o {out} {src}',
        'C++': 'g++ -O2 -std=c++17 -o {out} {src}',
        'Java': 'javac {src}',
        'Python': None,  # 解释型，不编译
    }
    EXT = {'C': '.c', 'C++': '.cpp', 'Java': '.java', 'Python': '.py'}
    FILENAME = {'C': 'main', 'C++': 'main', 'Java': 'Main', 'Python': 'main'}

    src_file = os.path.join(tmp_dir, FILENAME[lang] + EXT[lang])
    with open(src_file, 'w', encoding='utf-8') as f:
        f.write(code)

    # 编译阶段
    compile_cmd = COMPILE_CMD.get(lang)
    if compile_cmd:
        out_file = os.path.join(tmp_dir, 'main')
        cmd = compile_cmd.format(src=src_file, out=out_file)
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, cwd=tmp_dir)
            if proc.returncode != 0:
                submission.status = 'CE'
                submission.error_info = proc.stderr[:2000]
                submission.save(update_fields=['status', 'error_info'])
                _async_ai_feedback(submission.id, problem.id)
                return {'status': 'CE', 'error_info': proc.stderr[:2000], 'ai_feedback': ''}
        except subprocess.TimeoutExpired:
            submission.status = 'CE'
            submission.error_info = '编译超时'
            submission.save(update_fields=['status', 'error_info'])
            return {'status': 'CE', 'error_info': '编译超时', 'ai_feedback': ''}

    # 运行阶段：逐测试点执行
    time_limit_sec = problem.time_limit / 1000.0 + 1  # 多给 1 秒容差
    max_time = 0.0
    max_memory_kb = 0
    mem_limit_kb = problem.memory_limit * 1024

    import sys as _sys
    import time as _time
    import threading as _threading
    _win = _sys.platform == 'win32'
    _exe = 'main.exe' if _win else 'main'
    _py = _sys.executable  # 当前 Python 解释器路径，跨平台兼容

    _exe_path = os.path.join(tmp_dir, _exe)
    RUN_CMD_LIST = {
        'C':      [_exe_path],
        'C++':    [_exe_path],
        'Java':   ['java', '-cp', tmp_dir, 'Main'],
        'Python': [str(_py), str(src_file)],
    }
    run_cmd_list = RUN_CMD_LIST[lang]

    def _read_rss_kb(pid):
        try:
            with open(f'/proc/{pid}/status') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        return int(line.split()[1])
        except (OSError, ValueError):
            pass
        return 0

    def _normalize(s):
        """统一行尾为 \n，去掉每行尾部空格，去掉末尾空行。"""
        return '\n'.join(line.rstrip() for line in s.replace('\r\n', '\n').replace('\r', '\n').rstrip().split('\n'))

    for tc in test_cases:
        peak_mem = [0]
        stop_mon = _threading.Event()
        try:
            t0 = _time.monotonic()
            proc = subprocess.Popen(
                run_cmd_list,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, cwd=tmp_dir,
            )
            if not _win:
                def _monitor(pid=proc.pid):
                    while not stop_mon.is_set():
                        rss = _read_rss_kb(pid)
                        if rss > peak_mem[0]:
                            peak_mem[0] = rss
                        stop_mon.wait(0.05)
                _threading.Thread(target=_monitor, daemon=True).start()
            try:
                stdout_data, stderr_data = proc.communicate(
                    input=tc.input_data, timeout=time_limit_sec,
                )
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                raise
            finally:
                stop_mon.set()
        except subprocess.TimeoutExpired:
            submission.status = 'TLE'
            submission.save(update_fields=['status'])
            _async_ai_feedback(submission.id, problem.id)
            return {'status': 'TLE', 'ai_feedback': ''}

        elapsed = _time.monotonic() - t0
        if elapsed > max_time:
            max_time = elapsed
        if peak_mem[0] > max_memory_kb:
            max_memory_kb = peak_mem[0]

        if peak_mem[0] > mem_limit_kb:
            submission.status = 'MLE'
            submission.memory_used = peak_mem[0]
            submission.save(update_fields=['status', 'memory_used'])
            _async_ai_feedback(submission.id, problem.id)
            return {'status': 'MLE', 'ai_feedback': ''}

        if proc.returncode != 0:
            submission.status = 'RE'
            submission.error_info = stderr_data[:1000]
            submission.save(update_fields=['status', 'error_info'])
            _async_ai_feedback(submission.id, problem.id)
            return {'status': 'RE', 'error_info': stderr_data[:500], 'ai_feedback': ''}

        # 比较输出（规范化行尾、行尾空格、末尾空行）
        actual = _normalize(stdout_data)
        expected = _normalize(tc.expected_output)
        if actual != expected:
            submission.status = 'WA'
            submission.save(update_fields=['status'])
            _async_ai_feedback(submission.id, problem.id)
            return {'status': 'WA', 'ai_feedback': ''}

    # 全部通过
    submission.status = 'AC'
    submission.time_used = int(max_time * 1000) if max_time > 0 else 0
    submission.memory_used = max_memory_kb if max_memory_kb > 0 else None
    submission.save(update_fields=['status', 'time_used', 'memory_used'])

    # 判重：同一用户同一题目只计一次 AC
    already_ac = Submission.objects.filter(
        user=submission.user, problem=problem, status='AC'
    ).exclude(id=submission.id).exists()

    if not already_ac:
        Problem.objects.filter(id=problem.id).update(ac_count=F('ac_count') + 1)
        UserProfile.objects.filter(user=submission.user).update(ac_count=F('ac_count') + 1)
        _update_rating(submission.user, problem)

    # 比赛提交：更新罚时
    if submission.contest:
        update_contest_score(submission)

    _async_ai_feedback(submission.id, problem.id)
    return {'status': 'AC', 'time_used': submission.time_used, 'ai_feedback': ''}


def update_contest_score(submission):
    """更新比赛参与者的分数和罚时 — 对应技术方案书 §4.2.1"""
    contest = submission.contest
    if contest.rule_type != 'ICPC':
        return

    problem_id = submission.problem_id

    # 只处理该题首次 AC，重复 AC 不改变分数
    first_ac = (
        Submission.objects.filter(
            user=submission.user, contest=contest, problem_id=problem_id, status='AC'
        ).order_by('submitted_at').values('id').first()
    )
    if not first_ac or first_ac['id'] != submission.id:
        return

    ContestParticipant.objects.get_or_create(contest=contest, user=submission.user)

    ac_minutes = int((submission.submitted_at - contest.start_time).total_seconds() / 60)
    wrong_count = Submission.objects.filter(
        user=submission.user, contest=contest, problem_id=problem_id,
        submitted_at__lt=submission.submitted_at,
    ).exclude(status__in=['AC', 'Pending', 'Judging']).count()

    ContestParticipant.objects.filter(
        contest=contest, user=submission.user
    ).update(
        score=F('score') + 1,
        penalty=F('penalty') + ac_minutes + wrong_count * 20,
    )
