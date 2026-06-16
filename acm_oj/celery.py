"""Celery 应用入口。

评测与 AI 反馈通过 Celery 任务异步执行，由独立 worker 进程消费。
启动 worker：
    celery -A acm_oj worker -l info             # Linux 生产
    celery -A acm_oj worker -l info --pool=solo  # Windows 本地调试（prefork 不支持 Windows）
"""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'acm_oj.settings')

app = Celery('acm_oj')

# 所有以 CELERY_ 为前缀的 Django 设置都会被读取（见 settings.py）
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现各 app 下的 tasks.py
app.autodiscover_tasks()


# 长驻 worker 里 Django 的 DB 连接可能被 MySQL wait_timeout 掐断（"server has gone
# away"）。在每个任务前后关掉失效连接，让 Django 下次自动重连。
# 仅在真实 worker（非 eager）下生效：eager 模式任务可能嵌在请求的事务里，
# 此时关连接会破坏外层 atomic 块，且开发态根本没有长驻 worker、无需保活。
from celery.signals import task_postrun, task_prerun  # noqa: E402
from django.db import close_old_connections  # noqa: E402


def _recycle_db_connections(*args, **kwargs):
    from django.conf import settings as _s
    if not getattr(_s, 'CELERY_TASK_ALWAYS_EAGER', False):
        close_old_connections()


task_prerun.connect(_recycle_db_connections)
task_postrun.connect(_recycle_db_connections)
