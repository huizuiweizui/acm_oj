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
    'star',
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
# DB_ENGINE=mysql（默认，生产）| sqlite（本地快速体验 / 单元测试，无需安装 MySQL）
DB_ENGINE = env('DB_ENGINE', default='mysql').lower()

if DB_ENGINE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / env('DB_NAME', default='db.sqlite3'),
        }
    }
else:
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

# ===================== 缓存（限流计数依赖） =====================
# 限流计数存在 Django 缓存里。配置 REDIS_URL 后多个 Web 进程共享同一份计数，
# 限流才真正准确；留空则退回进程内存（单进程可用，多进程时每进程各算各的）。
REDIS_URL = env('REDIS_URL', default='')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'acm-oj-cache',
        }
    }

# ===================== REST Framework + JWT =====================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    # 全局只限匿名请求（防爬），额度给得很宽松，正常浏览不会触发。
    # 不设全局 user 限流：前端提交后每 2 秒轮询一次评测结果，按用户限流会误伤。
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon':     env('THROTTLE_ANON',     default='300/min'),
        # 以下为按视图作用域的精确限流（见 api_views.py 的 throttle_scope）
        'login':    env('THROTTLE_LOGIN',    default='10/min'),   # 防口令爆破
        'register': env('THROTTLE_REGISTER', default='30/hour'),  # 防批量注册（校园 NAT 共用出口 IP，故给得较宽）
        'submit':   env('THROTTLE_SUBMIT',   default='30/min'),   # 防刷评测，比赛正常提交够用
        'run':      env('THROTTLE_RUN',      default='30/min'),   # 自定义运行同样会执行代码
        'ai':       env('THROTTLE_AI',       default='30/hour'),  # 每次调用 LLM 都花钱
        # 星语对话助手：学生学习时会连续提问，额度比通用问答宽
        'star_ai':  env('THROTTLE_STAR_AI',  default='120/hour'),
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

# Django 后台（/django-admin/）表单的可信来源。经 nginx 同源访问时不用配；
# 前面再套一层反代 / CDN、导致 Origin 与 Host 对不上时才需要，如 https://oj.example.com
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

# ===================== HTTPS（生产：nginx 终止 TLS） =====================
# 用公网 IP + HTTP 演示时保持 False。有域名与证书、nginx 换成 site-https.conf 后设为 True，
# 一次打开 HTTPS 相关的安全项（manage.py check --deploy 的 W004/W008/W012/W016）。
USE_HTTPS = env.bool('USE_HTTPS', default=False)
if USE_HTTPS:
    # nginx 终止 TLS 后以 HTTP 转发给 gunicorn，靠这个头告诉 Django 原始请求是 HTTPS。
    # nginx 每次都覆盖该头（deploy/nginx/site-common.inc），客户端伪造不了。
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # 先给 1 小时，确认全站 HTTPS 正常后再调大——浏览器会记住 HSTS，配错了不好撤回
    SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=3600)

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# ===== 评测配置 =====
JUDGE_TEMP_DIR = os.path.join(BASE_DIR, 'judge_tmp')
JUDGE_TIMEOUT = 10

# 评测并发上限：进程内 worker 池同时最多跑这么多个评测，其余排队等待。
# 按评测机 CPU 核数配置（Docker 沙箱下每个评测约占 1 核）。多进程部署时
# 总并发 = Web 进程数 × JUDGE_WORKERS。
JUDGE_WORKERS = env.int('JUDGE_WORKERS', default=4)

# 自定义运行（题目页的"运行"按钮）的并发上限，与评测名额相互独立，
# 保证它抢不走判题的 worker。0 表示取 JUDGE_WORKERS 的一半（至少 1）。
JUDGE_RUN_WORKERS = env.int('JUDGE_RUN_WORKERS', default=0)
# 排不到名额时最多等几秒，超过就回 503，避免请求堆积把 web 进程占满。
JUDGE_RUN_QUEUE_WAIT = env.float('JUDGE_RUN_QUEUE_WAIT', default=15.0)

# 单个测试点输出硬上限（KB）。选手程序疯狂打印时，主机读取管道会把输出全缓冲进内存，
# 超过此上限即强制终止并判 OLE，保护评测机不被打爆。默认 64 MB。
JUDGE_OUTPUT_LIMIT_KB = env.int('JUDGE_OUTPUT_LIMIT_KB', default=65536)

# ── Docker 沙箱加固（仅 USE_DOCKER_SANDBOX=True 时生效）──
# 运行容器内的非 root 用户。默认 nobody，杜绝以 root 执行选手代码（配合 cap-drop 抵御内核提权）。
# 若部署环境权限特殊导致只读挂载不可读，可设为空字符串临时退回 root 执行。
JUDGE_SANDBOX_RUN_USER = env('JUDGE_SANDBOX_RUN_USER', default='nobody')
# 容器内可打开的文件描述符上限，防止 fd 耗尽。JVM 需要较多，给足 1024。
JUDGE_SANDBOX_NOFILE = env.int('JUDGE_SANDBOX_NOFILE', default=1024)

# 沙箱隔离 — 生产环境必须设为 True，开发/Windows 可保持 False
# True  → 每次评测启动 Docker 容器隔离执行（需提前 build Dockerfile.sandbox）
# False → 直接在主机进程执行（无隔离，仅限本地开发）
USE_DOCKER_SANDBOX = env.bool('USE_DOCKER_SANDBOX', default=False)
JUDGE_DOCKER_IMAGE = env('JUDGE_DOCKER_IMAGE', default='acm-oj-sandbox:latest')

# ===== AI 评测（可选，留空则禁用） =====
LLM_API_KEY = env('LLM_API_KEY', default='')
LLM_API_URL = env('LLM_API_URL', default='')
LLM_MODEL   = env('LLM_MODEL',   default='')

# AI 反馈的后台并发上限。每个 worker 会挂一次几十秒的 LLM 请求并占一条数据库连接，
# 给小一点即可——反馈晚几秒无所谓，绝不该和评测抢资源。
AI_FEEDBACK_WORKERS = env.int('AI_FEEDBACK_WORKERS', default=2)

# ===== RAG 向量检索（可选） =====
# EMBED_API_KEY / EMBED_API_BASE 留空时自动复用 LLM_API_KEY / LLM_API_URL 的 base
EMBED_API_KEY  = env('EMBED_API_KEY',  default='')
EMBED_API_BASE = env('EMBED_API_BASE', default='')   # e.g. https://ark.cn-beijing.volces.com/api/v3
EMBED_MODEL    = env('EMBED_MODEL',    default='')   # e.g. ep-xxxx（Ark embedding 端点）

# ===================== 日志 =====================
# Django 默认只在 DEBUG=True 时把日志打到控制台：生产（DEBUG=False）下 500 错误的堆栈、
# 评测线程里的异常哪里都看不到。生产环境统一输出到 stderr，用 docker compose logs web 查看。
# 开发环境沿用 Django 默认配置，避免同一条日志打两遍。
if not DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'plain': {'format': '%(asctime)s %(levelname)s %(name)s: %(message)s'},
        },
        'handlers': {
            'console': {'class': 'logging.StreamHandler', 'formatter': 'plain'},
        },
        'root': {'handlers': ['console'], 'level': env('LOG_LEVEL', default='INFO')},
    }
