"""Celery 异步任务：代码评测 + AI 反馈 + 自定义运行 + 定时维护。

把原先的 threading.Thread 改为 Celery 任务，由独立 worker 进程消费：
- 评测并发上限 = worker 并发数（CELERY_WORKER_CONCURRENCY），防止考试洪峰打爆机器
- 进程重启不丢任务（任务持久化在 Redis 中）
- 可与 Web 分机部署，单独扩容评测

所有重依赖都在函数内部延迟导入，保证 worker 启动时 autodiscover 导入本模块不触发循环引用。
"""
import logging

from celery import shared_task

logger = logging.getLogger('judge')


# ── 评测 ────────────────────────────────────────────────────────────
@shared_task(name='judge.judge_submission')
def judge_submission_task(submission_id):
    """评测一条提交：先置 Judging，调用同步评测引擎，异常兜底为 RE。

    不做自动重试 —— 评测会用 F() 累加 AC 计数并更新 Rating，重复执行会双计。
    """
    from .models import Submission
    from .services.judger import judge_submission

    try:
        sub = Submission.objects.select_related('problem').get(id=submission_id)
    except Submission.DoesNotExist:
        return

    sub.status = 'Judging'
    sub.save(update_fields=['status'])
    try:
        judge_submission(sub, sub.problem)
    except Exception:
        # 兜底：评测内部异常时置 RE，避免前端无限轮询
        logger.exception('评测失败 submission_id=%s', submission_id)
        Submission.objects.filter(id=submission_id).update(
            status='RE', error_info='Internal judge error',
        )


# ── AI 反馈 ─────────────────────────────────────────────────────────
@shared_task(name='judge.ai_feedback')
def ai_feedback_task(submission_id, problem_id):
    """评测结束后异步生成 AI 反馈，失败静默（不影响已返回的 verdict）。"""
    from .models import Problem, Submission
    from .services.ai_feedback import _ai_call, _ai_suggest_prompt

    try:
        sub = Submission.objects.get(id=submission_id)
        prob = Problem.objects.get(id=problem_id)
        fb = _ai_call(_ai_suggest_prompt(sub, prob))
        if fb:
            sub.ai_feedback = fb
            sub.save(update_fields=['ai_feedback'])
    except Exception:
        logger.warning('AI 反馈生成失败 submission_id=%s', submission_id, exc_info=True)


# ── 自定义运行（不保存提交，结果走 Celery result backend）────────────
@shared_task(name='judge.custom_run')
def custom_run_task(code, language, custom_input):
    """编译并运行用户代码，返回 {status, output, error}；与评测共用沙箱与并发闸门。"""
    import shutil
    import tempfile

    from .services.sandbox import compile_code, run_code, source_path

    tmp_dir = tempfile.mkdtemp(prefix='api_run_')
    try:
        src = source_path(language, tmp_dir)
        with open(src, 'w', encoding='utf-8') as f:
            f.write(code)

        ok, err_msg = compile_code(language, tmp_dir)
        if not ok:
            return {'status': 'CE', 'output': '', 'error': err_msg[:2000]}

        returncode, stdout_data, stderr_data, timed_out = run_code(
            language, tmp_dir, custom_input, timeout_sec=10.0, memory_mb=256,
        )
        if timed_out:
            run_status = 'TLE'
        elif returncode == 137:
            run_status = 'MLE'
        elif returncode != 0:
            run_status = 'RE'
        else:
            run_status = 'OK'

        return {
            'status': run_status,
            'output': stdout_data[:4096],
            'error': stderr_data[:1024] if run_status != 'OK' else '',
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ── 定时维护任务（Celery Beat 调度，见 settings.CELERY_BEAT_SCHEDULE）──
@shared_task(name='judge.reap_stuck_submissions')
def reap_stuck_submissions(max_age_minutes=15):
    """把卡在 Judging 超过阈值的提交置 RE（worker 崩溃/重启的兜底）。

    只处理 Judging（已被 worker 取走但卡死）；Pending 不动 —— 考试洪峰下排队中的
    Pending 是正常的，误判会把排队提交错杀。任务硬超时 5min，>15min 必是死任务。
    """
    from datetime import timedelta

    from django.utils import timezone

    from .models import Submission

    cutoff = timezone.now() - timedelta(minutes=max_age_minutes)
    n = Submission.objects.filter(status='Judging', submitted_at__lt=cutoff).update(
        status='RE', error_info='评测超时未完成（系统自动标记，请重新提交）',
    )
    if n:
        logger.warning('reap_stuck_submissions: 回收 %s 条卡死提交', n)
    return n


@shared_task(name='judge.cleanup_judge_tmp')
def cleanup_judge_tmp(max_age_hours=2):
    """清理遗留的评测临时目录（judge_* / api_run_*）。"""
    import glob
    import os
    import shutil
    import tempfile
    import time

    base = tempfile.gettempdir()
    cutoff = time.time() - max_age_hours * 3600
    removed = 0
    for pattern in ('judge_*', 'api_run_*'):
        for path in glob.glob(os.path.join(base, pattern)):
            try:
                if os.path.isdir(path) and os.path.getmtime(path) < cutoff:
                    shutil.rmtree(path, ignore_errors=True)
                    removed += 1
            except OSError:
                pass
    return removed


@shared_task(name='judge.flush_expired_tokens')
def flush_expired_tokens():
    """清理过期的 JWT 黑名单 token（simplejwt 的 token_blacklist 表会持续增长）。"""
    from django.core.management import call_command

    call_command('flushexpiredtokens')
