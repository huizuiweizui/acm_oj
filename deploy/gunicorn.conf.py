"""
gunicorn 配置（deploy/docker-compose.yml 的 web 服务；数值都可在 deploy/.env 覆盖）。

── worker 模型：gthread（多进程 × 每进程多线程）────────────────────────────
本项目有三类"长请求"，同步 worker 一个请求就占死一个进程：
  · 星语教师端"大模型改造"：同步请求，生成 → 校验 → 修复最多 3 轮（star/services/adapt.py），
    前端给了 180 秒超时（frontend/src/api/star.js 的 LONG）；
  · AI 问答 /api/ai/ask/：SSE 流式输出，整段回答期间连接一直开着；
  · 自定义运行 / 星语排序题：请求线程原地等沙箱跑完，排不到名额时还要排队最多
    JUDGE_RUN_QUEUE_WAIT 秒。
gthread 让这些请求各占一个线程，不会把整个进程堵住。

── 进程数与评测并发（judge/services/judge_queue.py 顶部注释）──────────────
评测线程池、自定义运行名额、AI 反馈池都是"每个 gunicorn worker 进程各一份"：
    评测总并发       = GUNICORN_WORKERS × JUDGE_WORKERS
    自定义运行总并发 = GUNICORN_WORKERS × JUDGE_RUN_WORKERS（0 表示取 JUDGE_WORKERS 的一半，至少 1）
    AI 反馈总并发    = GUNICORN_WORKERS × AI_FEEDBACK_WORKERS
    同时在处理的请求 = GUNICORN_WORKERS × GUNICORN_THREADS
每个评测容器占约 1 核（--cpus=1），所以"评测总并发 ≈ CPU 核数"。
例：2 核机器 → GUNICORN_WORKERS=2、JUDGE_WORKERS=1；4 核 → 2 × 2。

── 不要开的选项 ───────────────────────────────────────────────────────────
  · max_requests：评测队列只在 worker 进程内存里，定期回收 worker 会丢掉排队中的评测；
  · preload_app：评测线程池、数据库连接必须在 fork 之后的 worker 里各自创建。
"""
import os


def _int(name, default):
    return int(os.environ.get(name, '') or default)


bind = '0.0.0.0:8000'
worker_class = 'gthread'
workers = _int('GUNICORN_WORKERS', 2)
threads = _int('GUNICORN_THREADS', 8)

# gthread 下 timeout 是"worker 多久没心跳就被杀"，不限制单个请求的时长——主循环每秒都在
# 心跳，线程里跑 3 分钟的大模型请求不会被误杀。仍按 ≥ 180 秒配置：万一换回 sync worker，
# 这个值就直接成了请求时长上限，需要盖住"大模型改造"最多 3 轮的耗时。
timeout = _int('GUNICORN_TIMEOUT', 300)
# 重启 / 发版时给在途请求的收尾时间；超时仍未结束的评测由下次启动的 recover_pending 捞回。
# docker-compose.yml 里 web 的 stop_grace_period 必须比它大，否则 Docker 会先 SIGKILL。
graceful_timeout = _int('GUNICORN_GRACEFUL_TIMEOUT', 60)
keepalive = 5

# 心跳文件放内存盘：放在磁盘（或挂载卷）上时 os.fchmod 可能阻塞 worker
worker_tmp_dir = '/dev/shm'

# 访问日志由 nginx 记（带请求耗时），这里只留错误日志，输出到容器 stdout/stderr
accesslog = None
errorlog = '-'
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')


# ── 重启后恢复未完成的评测 ─────────────────────────────────────────────────
# judge/apps.py 的 ready() 只认 argv 里恰好等于 'gunicorn' 的参数，而 gunicorn 实际的
# argv[0] 是完整路径（/usr/local/bin/gunicorn），所以由这里显式调用 recover_pending()。
# 必须只在一个 worker 里做：每个 worker 都捞一遍，同一条提交会被重复评测（AC 数、Rating
# 会被加两次）。做法是 master 每次启动放一个"令牌"文件，第一个初始化完的 worker 删掉它
# 并负责恢复（删除是原子操作，只有一个能成功）；之后 worker 崩溃重启、HUP 重载都不再恢复。
# 若日后改了 apps.py 让它在 gunicorn 下也触发恢复，要删掉这两个钩子——ready() 会在
# 每个 worker 里各跑一次，再加上这里就更多了。
_RECOVER_TOKEN = '/dev/shm/acm-oj-recover-pending'


def when_ready(server):
    """master 启动完成、尚未派生 worker 时调用。"""
    with open(_RECOVER_TOKEN, 'w'):
        pass


def post_worker_init(worker):
    """worker 加载完 Django 后调用：拿到令牌的那一个把卡在 Pending / Judging 的提交重新入队。"""
    try:
        os.remove(_RECOVER_TOKEN)
    except FileNotFoundError:
        return

    from django.db import connections
    from judge.services.judge_queue import recover_pending
    try:
        n = recover_pending()
        worker.log.info('recover_pending: %d 个未完成的评测已重新入队', n)
    except Exception:
        worker.log.exception('recover_pending 失败')
    finally:
        # 恢复在 worker 主线程里查库；主线程之后不处理请求，连接留着只会空耗
        connections.close_all()
