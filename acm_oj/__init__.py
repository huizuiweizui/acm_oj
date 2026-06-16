"""Django 启动时加载 Celery 应用，使 @shared_task 能注册到该实例。"""
from .celery import app as celery_app

__all__ = ('celery_app',)
