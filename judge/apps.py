import os
import sys

from django.apps import AppConfig

# 仅在真正对外提供服务时才恢复评测队列；migrate 等命令不应触发评测。
_SERVER_COMMANDS = {'runserver', 'gunicorn', 'uvicorn', 'daphne'}


class JudgeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'judge'
    verbose_name = 'ACM 评测'

    def ready(self):
        argv = sys.argv
        is_server = any(cmd in argv for cmd in _SERVER_COMMANDS) or not argv
        if not is_server:
            return
        # runserver 的自动重载会 fork 两次，只在真正的工作进程里恢复一次
        if 'runserver' in argv and os.environ.get('RUN_MAIN') != 'true':
            return
        try:
            from .services.judge_queue import recover_pending
            recover_pending()
        except Exception:
            # 数据库尚未就绪（如首次 migrate 前）时静默跳过，不阻塞启动
            pass
