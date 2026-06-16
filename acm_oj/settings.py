"""
ACM 算法竞赛平台 - Django 配置
"""
import os
import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),           # 安全默认：生产关闭调试
    ALLOWED_HOSTS=(list, []),      # 安全默认：无 .env 时拒绝所有 Host
    CORS_ORIGINS=(list, ['http://localhost:5173']),
)
environ.Env.read_env(BASE_DIR / '.env')

# SECRET_KEY 无默认值 — .env 缺失或未设置时 Django 启动即报 ImproperlyConfigured
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'judge',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'acm_oj.urls'

_FRONTEND_DIST = BASE_DIR / 'frontend' / 'dist'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [_FRONTEND_DIST] if _FRONTEND_DIST.exists() else [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'acm_oj.wsgi.application'

# ===================== 数据库配置 =====================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_NAME', default='acm_oj'),
        'USER': env('DB_USER', default='root'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='127.0.0.1'),
        'PORT': env('DB_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        # 连接复用，减少每请求握手开销；worker 侧由 celery.py 的信号关旧连接兜底
        'CONN_MAX_AGE': env.int('DB_CONN_MAX_AGE', default=60),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = []
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ===================== REST Framework + JWT =====================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    # 限流：只对设置了 throttle_scope 的视图生效（提交 / 自定义运行），其余不受影响
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'submit': env('THROTTLE_SUBMIT', default='30/min'),
        'run': env('THROTTLE_RUN', default='20/min'),
    },
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(hours=8),   # 默认 5 分钟太短，开发/生产统一 8 小时
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
    'ROTATE_REFRESH_TOKENS':  False,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

CORS_ALLOWED_ORIGINS = env('CORS_ORIGINS')

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# ===== 评测配置 =====
JUDGE_TEMP_DIR = os.path.join(BASE_DIR, 'judge_tmp')
JUDGE_TIMEOUT = 10

# 沙箱隔离 — 生产环境必须设为 True，开发/Windows 可保持 False
# True  → 每次评测启动 Docker 容器隔离执行（需提前 build Dockerfile.sandbox）
# False → 直接在主机进程执行（无隔离，仅限本地开发）
USE_DOCKER_SANDBOX = env.bool('USE_DOCKER_SANDBOX', default=False)
JUDGE_DOCKER_IMAGE = env('JUDGE_DOCKER_IMAGE', default='acm-oj-sandbox:latest')

# ===== AI 评测（可选，留空则禁用） =====
LLM_API_KEY = env('LLM_API_KEY', default='')
LLM_API_URL = env('LLM_API_URL', default='')
LLM_MODEL   = env('LLM_MODEL',   default='')

# ===== RAG 向量检索（可选） =====
# EMBED_API_KEY / EMBED_API_BASE 留空时自动复用 LLM_API_KEY / LLM_API_URL 的 base
EMBED_API_KEY  = env('EMBED_API_KEY',  default='')
EMBED_API_BASE = env('EMBED_API_BASE', default='')   # e.g. https://ark.cn-beijing.volces.com/api/v3
EMBED_MODEL    = env('EMBED_MODEL',    default='')   # e.g. ep-xxxx（Ark embedding 端点）

# ===================== Celery 异步任务队列（评测 + AI 反馈） =====================
# 评测 / AI 反馈从线程改为 Celery 任务，由独立 worker 进程消费：
#   - 评测并发上限 = worker 并发数，防考试洪峰打爆机器
#   - 进程重启不丢任务（Redis 持久化）；可与 Web 分机部署，单独扩容评测
# 开发：DEBUG=True 时默认 eager（同步执行，免装 Redis/worker，行为同以前）
# 生产：DEBUG=False 自动走真实队列，需先启动 Redis，再开 worker：
#   celery -A acm_oj worker -l info             # Linux 生产
#   celery -A acm_oj worker -l info --pool=solo  # Windows 本地调试
REDIS_URL = env('REDIS_URL', default='redis://127.0.0.1:6379/0')
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default=REDIS_URL)
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default=REDIS_URL)
# 留空跟随 DEBUG：开发同步、生产异步；可用 .env 显式覆盖
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=DEBUG)
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True   # 让自定义运行能区分「排队中」与「运行中」
# 单条评测任务硬/软超时（兜底防卡死 worker；单测试点超时由沙箱另行控制）
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 270
# 评测任务重：每次只预取 1 个，跑满若干个后回收子进程防内存泄漏
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 200
# 同时最多几个评测（= 并发 Docker 容器数，按服务器 CPU 核数设）
CELERY_WORKER_CONCURRENCY = env.int('CELERY_WORKER_CONCURRENCY', default=4)

# 定时维护任务（需单独起 beat 进程：celery -A acm_oj beat -l info）
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'reap-stuck-submissions': {
        'task': 'judge.reap_stuck_submissions',
        'schedule': 300.0,                       # 每 5 分钟回收卡死的评测
    },
    'cleanup-judge-tmp': {
        'task': 'judge.cleanup_judge_tmp',
        'schedule': crontab(minute=0),           # 每小时清理评测临时目录
    },
    'flush-expired-tokens': {
        'task': 'judge.flush_expired_tokens',
        'schedule': crontab(hour=4, minute=0),   # 每天 04:00 清过期 JWT 黑名单
    },
}

# ===================== 缓存（生产用 Redis，开发用本地内存免装 Redis）==========
if DEBUG:
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
else:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'IGNORE_EXCEPTIONS': True,        # Redis 抖动时降级，不影响主流程
            },
        }
    }

# ===================== 日志 =====================
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{asctime} [{levelname}] {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'acm_oj.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },
    'root': {'handlers': ['console', 'file'], 'level': 'INFO'},
    'loggers': {
        'django': {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
        'judge':  {'handlers': ['console', 'file'], 'level': 'INFO', 'propagate': False},
    },
}

# ===================== 生产安全头（仅 DEBUG=False 启用）=====================
if not DEBUG:
    # Nginx 终止 HTTPS，靠转发头告诉 Django 原始协议是 https
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
