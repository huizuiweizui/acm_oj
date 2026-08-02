"""
评测队列 —— 固定大小的 worker 池 + 无界等待队列。

问题背景：
    原实现每次提交都 `threading.Thread(...).start()`，无上限。比赛场景下
    上百人同时交题会瞬间起上百个线程 / Docker 容器，把评测机 CPU、内存打满，
    结果就是所有提交一起超时。

解决方式：
    进程内维护一个 `ThreadPoolExecutor(max_workers=JUDGE_WORKERS)`。
    提交只是把任务丢进池子（内部队列无界，立即返回），最多同时跑
    JUDGE_WORKERS 个评测，其余排队等待。这样并发被牢牢限制住，
    部署上不引入 Celery / Redis，保持单进程即可运行。

注意：
    线程池随 Web 进程存在。若用 gunicorn 起多个 worker 进程，每个进程各有
    一个池子，总并发 = 进程数 × JUDGE_WORKERS —— 按评测机核数配置这两个值即可。
"""
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings

logger = logging.getLogger(__name__)

_MAX_WORKERS: int = int(getattr(settings, 'JUDGE_WORKERS', 4))

# 懒初始化：第一次入队时才创建线程池，避免在 migrate 等无需评测的命令里凭空起线程。
_executor: ThreadPoolExecutor | None = None
_lock = threading.Lock()


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        with _lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(
                    max_workers=_MAX_WORKERS,
                    thread_name_prefix='judge',
                )
                logger.info('评测线程池已启动，max_workers=%d', _MAX_WORKERS)
    return _executor


def _judge_task(submission_id: int, problem_id: int) -> None:
    """在 worker 线程里执行单次评测。异常兜底为 RE，保证前端不会一直轮询。"""
    # 延迟导入，避免模块循环引用（services -> views -> services）
    from ..models import Problem, Submission
    from ..services.judger import judge_submission

    try:
        sub = Submission.objects.get(id=submission_id)
        prob = Problem.objects.get(id=problem_id)
        sub.status = 'Judging'
        sub.save(update_fields=['status'])
        judge_submission(sub, prob)
    except Exception:
        logger.exception('评测失败 submission_id=%s', submission_id)
        from ..models import Submission
        Submission.objects.filter(id=submission_id).update(
            status='RE', error_info='Internal judge error',
        )


def enqueue(submission_id: int, problem_id: int) -> None:
    """把一次评测放入队列，立即返回；最多 JUDGE_WORKERS 个并发执行。"""
    _get_executor().submit(_judge_task, submission_id, problem_id)


def recover_pending() -> int:
    """
    重新入队所有卡在 Pending / Judging 的提交。

    进程重启会丢掉内存里排队/在跑的任务，这些提交会永远停在 Pending/Judging。
    在应用启动时调用一次即可把它们捞回来。返回重新入队的数量。
    """
    from ..models import Submission

    stuck_ids = list(
        Submission.objects
        .filter(status__in=['Pending', 'Judging'])
        .values_list('id', 'problem_id')
    )
    for sub_id, prob_id in stuck_ids:
        enqueue(sub_id, prob_id)
    if stuck_ids:
        logger.info('恢复 %d 个未完成的评测', len(stuck_ids))
    return len(stuck_ids)
