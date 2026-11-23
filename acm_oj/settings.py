"""
ACM 算法竞赛平台 - Django 配置
"""
import os
import environ
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

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
FRONTEND_DEV_ORIGIN = env('FRONTEND_DEV_ORIGIN', default='http://localhost:5173').rstrip('/')

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
if not DEBUG and not USE_DOCKER_SANDBOX:
    raise ImproperlyConfigured(
        '生产环境必须设置 USE_DOCKER_SANDBOX=True。'
    )
JUDGE_DOCKER_IMAGE = env('JUDGE_DOCKER_IMAGE', default='acm-oj-sandbox:latest')
JUDGE_WINDOWS_USE_MSVC = env.bool('JUDGE_WINDOWS_USE_MSVC', default=False)

# ===== AI 评测（可选，留空则禁用） =====
LLM_API_KEY = env('LLM_API_KEY', default='')
LLM_API_URL = env('LLM_API_URL', default='')
LLM_MODEL   = env('LLM_MODEL',   default='')

# ===== RAG 向量检索（可选） =====
# EMBED_API_KEY / EMBED_API_BASE 留空时自动复用 LLM_API_KEY / LLM_API_URL 的 base
EMBED_API_KEY  = env('EMBED_API_KEY',  default='')
EMBED_API_BASE = env('EMBED_API_BASE', default='')   # e.g. https://ark.cn-beijing.volces.com/api/v3
EMBED_MODEL    = env('EMBED_MODEL',    default='')   # e.g. ep-xxxx（Ark embedding 端点）
