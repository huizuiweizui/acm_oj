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
    编译 → 逐测试点运行 → 对比输出
    代码执行通过 sandbox 模块隔离（生产需开启 USE_DOCKER_SANDBOX=True）。
    """
    test_cases = problem.test_cases.all().order_by('sort_order')
    if not test_cases.exists():
        # 无测试点：不评判，不计入 AC/Rating，等管理员补充测试数据后重测
        submission.status = 'NT'
        submission.save(update_fields=['status'])
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
        submission.save(update_fields=['status', 'error_info'])
        _async_ai_feedback(submission.id, problem.id)
        return {'status': 'CE', 'error_info': err_msg[:2000], 'ai_feedback': ''}

    # ── 运行阶段：逐测试点 ─────────────────────────────────────────────────
    time_limit_sec = problem.time_limit / 1000.0
    memory_mb = problem.memory_limit
    max_time_ms = 0

    for tc in test_cases:
        t0 = _time.monotonic()
        returncode, stdout_data, stderr_data, timed_out = run_code(
            lang, tmp_dir, tc.input_data, time_limit_sec, memory_mb,
        )
        elapsed_ms = int((_time.monotonic() - t0) * 1000)
        if elapsed_ms > max_time_ms:
            max_time_ms = elapsed_ms

        if timed_out:
            submission.status = 'TLE'
            submission.save(update_fields=['status'])
            _async_ai_feedback(submission.id, problem.id)
            return {'status': 'TLE', 'ai_feedback': ''}

        # exit 137 = SIGKILL by Docker OOM killer → MLE
        if returncode == 137:
            submission.status = 'MLE'
            submission.save(update_fields=['status'])
            _async_ai_feedback(submission.id, problem.id)
            return {'status': 'MLE', 'ai_feedback': ''}

        if returncode != 0:
            submission.status = 'RE'
            submission.error_info = stderr_data[:1000]
            submission.save(update_fields=['status', 'error_info'])
            _async_ai_feedback(submission.id, problem.id)
            return {'status': 'RE', 'error_info': stderr_data[:500], 'ai_feedback': ''}

        actual = _normalize(stdout_data)
        expected = _normalize(tc.expected_output)
        if actual != expected:
            submission.status = 'WA'
            submission.save(update_fields=['status'])
            _async_ai_feedback(submission.id, problem.id)
            return {'status': 'WA', 'ai_feedback': ''}

    # ── 全部通过 ──────────────────────────────────────────────────────────
    submission.status = 'AC'
    submission.time_used = max_time_ms
    submission.save(update_fields=['status', 'time_used'])

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
    return {'status': 'AC', 'time_used': max_time_ms, 'ai_feedback': ''}


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
