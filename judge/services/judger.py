import os
import tempfile
import time as _time

from django.db.models import F

from ..models import ContestParticipant, Problem, Submission, UserProfile
from .ai_feedback import _async_ai_feedback
from .rating import _update_rating
from .sandbox import compile_code, run_code, source_path


def _normalize(s):
    """Normalize line endings and trailing whitespace for output comparison."""
    return '\n'.join(
        line.rstrip()
        for line in s.replace('\r\n', '\n').replace('\r', '\n').rstrip().split('\n')
    )


def judge_submission(submission, problem):
    """
    评测引擎 — 对应技术方案书 §8.2
    编译 → 逐测试点运行 → 对比输出 → 收集每个测试点结果
    代码执行通过 sandbox 模块隔离（生产需开启 USE_DOCKER_SANDBOX=True）。
    """
    test_cases = problem.test_cases.all().order_by('sort_order')
    if not test_cases.exists():
        # 无测试点：不评判，不计入 AC/Rating，等管理员补充测试数据后重测
        submission.status = 'NT'
        submission.test_results = []
        submission.save(update_fields=['status', 'test_results'])
        _async_ai_feedback(submission.id, problem.id)
        return {'status': 'NT', 'ai_feedback': ''}

    lang = submission.language
    tmp_dir = tempfile.mkdtemp(prefix='judge_')
    src_file = source_path(lang, tmp_dir)
    with open(src_file, 'w', encoding='utf-8') as f:
        f.write(submission.code)

    # ── 编译阶段 ──────────────────────────────────────────────────────────
    ok, err_msg = compile_code(lang, tmp_dir)
    if not ok:
        submission.status = 'CE'
        submission.error_info = err_msg[:2000]
        submission.test_results = []
        submission.save(update_fields=['status', 'error_info', 'test_results'])
        _async_ai_feedback(submission.id, problem.id)
        return {'status': 'CE', 'error_info': err_msg[:2000], 'ai_feedback': ''}

    # ── 运行阶段：逐测试点（全部跑完，收集每个测试点结果） ────────────────
    time_limit_sec = problem.time_limit / 1000.0
    memory_mb = problem.memory_limit
    max_time_ms = 0
    overall_status = 'AC'
    last_re_error = ''
    case_results = []

    for idx, tc in enumerate(test_cases, 1):
        t0 = _time.monotonic()
        returncode, stdout_data, stderr_data, timed_out, output_exceeded = run_code(
            lang, tmp_dir, tc.input_data, time_limit_sec, memory_mb,
        )
        elapsed_ms = int((_time.monotonic() - t0) * 1000)

        if timed_out:
            case_status = 'TLE'
        elif returncode == 137:
            case_status = 'MLE'
        elif output_exceeded:
            case_status = 'OLE'
        elif returncode != 0:
            case_status = 'RE'
            last_re_error = stderr_data[:1000]
        else:
            actual = _normalize(stdout_data)
            expected = _normalize(tc.expected_output)
            case_status = 'AC' if actual == expected else 'WA'

        if case_status == 'AC':
            max_time_ms = max(max_time_ms, elapsed_ms)

        case_results.append({'idx': idx, 'status': case_status, 'time_ms': elapsed_ms})

        if overall_status == 'AC' and case_status != 'AC':
            overall_status = case_status

    # ── 保存结果 ──────────────────────────────────────────────────────────
    submission.status = overall_status
    submission.test_results = case_results
    if overall_status == 'AC':
        submission.time_used = max_time_ms
    elif overall_status == 'RE':
        submission.error_info = last_re_error
    submission.save(update_fields=['status', 'time_used', 'error_info', 'test_results'])

    if overall_status == 'AC':
        already_ac = Submission.objects.filter(
            user=submission.user, problem=problem, status='AC'
        ).exclude(id=submission.id).exists()

        if not already_ac:
            Problem.objects.filter(id=problem.id).update(ac_count=F('ac_count') + 1)
            UserProfile.objects.filter(user=submission.user).update(ac_count=F('ac_count') + 1)
            _update_rating(submission.user, problem)

    if submission.contest:
        update_contest_score(submission)

    _async_ai_feedback(submission.id, problem.id)
    return {'status': overall_status, 'time_used': max_time_ms, 'ai_feedback': ''}


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
