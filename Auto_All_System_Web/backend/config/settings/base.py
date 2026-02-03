"""
Django基础配置
所有环境通用的配置
"""

import os
import sys
from pathlib import Path
from datetime import timedelta

from celery.schedules import crontab

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-key-change-in-production")

# Application definition
INSTALLED_APPS = [
    # Django默认应用
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 第三方应用
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_yasg",  # API文档
    "channels",  # WebSocket
    # 自定义应用 - 核心系统
    "apps.accounts",
    "apps.zones",
    "apps.tasks",
    "apps.cards",
    "apps.payments",
    "apps.admin_panel",
    # 共享资源层
    "apps.integrations",
    "apps.integrations.google_accounts",
    "apps.integrations.bitbrowser",
    "apps.integrations.geekez",
    "apps.integrations.proxies",
    "apps.integrations.email",  # 邮件服务
    # 插件系统
    "apps.plugins.apps.PluginsConfig",  # 插件管理器（需要 ready() 触发 discover_plugins）
    # 业务插件
    "plugins.google_business",  # Google Business插件
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "auto_all_system"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "we85083288"),
        "HOST": os.getenv(
            "DB_HOST", "127.0.0.1"
        ),  # 强制使用IPv4，避免localhost解析为IPv6
        "PORT": os.getenv("DB_PORT", "5432"),
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": 600,
    }
}

# 让 `python manage.py test` 在没有本地 Postgres 的情况下也能跑起来。
# 仅在 test 命令时切换 sqlite，不影响 dev/prod。
if "test" in sys.argv:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

# Cache (Redis)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # 移除HiredisParser - 使用默认的PythonParser
            # 'PARSER_CLASS': 'redis.connection.HiredisParser',
            "PICKLE_VERSION": -1,
        },
        "KEY_PREFIX": "auto_all_system",
        "TIMEOUT": 300,
    }
}

# Channels (WebSocket)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(os.getenv("REDIS_HOST", "127.0.0.1"), 6379)],
        },
    },
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# 自定义User模型
AUTH_USER_MODEL = "accounts.User"

# REST Framework配置
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # 说明：前端存在轮询（任务进度、状态刷新等），按 day 计数会导致正常使用也很快触发 429。
        # 改为按 hour 计数，并提高额度，保证 UI 轮询可用。
        "anon": "300/hour",
        "user": "10000/hour",
        "task_create": "100/hour",
    },
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
}

# JWT配置
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# CORS配置
CORS_ALLOWED_ORIGINS = [
    "http://localhost",  # Nginx前端
    "http://localhost:80",
    "http://localhost:5173",  # 用户前端开发服务器
    "http://localhost:5174",  # 管理后台
]
CORS_ALLOW_CREDENTIALS = True

# URL配置
APPEND_SLASH = True  # Django默认会自动添加斜杠并重定向

# 代理配置 - 信任来自Nginx的头信息
# 这样Nginx可以控制SSL/HTTPS，Django通过X-Forwarded-Proto头识别
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Cookie安全性 - 根据环境变量动态控制
# 当ENABLE_HTTPS=true时，Cookie要求HTTPS；false时允许HTTP
SESSION_COOKIE_SECURE = os.getenv("ENABLE_HTTPS", "false").lower() == "true"
CSRF_COOKIE_SECURE = os.getenv("ENABLE_HTTPS", "false").lower() == "true"

# Celery配置
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30分钟超时

_GPT_TRACE_CLEANUP_ENABLED = os.getenv("GPT_TRACE_CLEANUP_ENABLED", "true").lower() in ["1", "true", "yes"]
if _GPT_TRACE_CLEANUP_ENABLED:
    CELERY_BEAT_SCHEDULE = {
        "gpt_business_trace_cleanup": {
            "task": "plugins.gpt_business.tasks.cleanup_trace_task",
            "schedule": crontab(hour=3, minute=30),
        }
    }
else:
    CELERY_BEAT_SCHEDULE = {}

# 加密密钥（用于敏感数据加密）
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "your-encryption-key-change-in-production")

# 比特浏览器API配置
# Docker环境下使用 host.docker.internal 访问宿主机服务
# 本地开发使用 127.0.0.1
_default_bitbrowser_host = (
    "host.docker.internal"
    if os.getenv("DJANGO_ENVIRONMENT") == "docker"
    else "127.0.0.1"
)
BITBROWSER_API_URL = os.getenv(
    "BITBROWSER_API_URL", f"http://{_default_bitbrowser_host}:54345"
)

# 日志配置
_ENABLE_FILE_LOG = True
try:
    _log_dir = BASE_DIR / "logs"
    _log_file = _log_dir / "django.log"

    # 目录可能由容器/脚本创建为 root，开发/测试环境下不可写。
    # 这里做一次轻量探测：不可写则禁用 file handler，避免 Django 启动直接报错。
    _log_dir.mkdir(parents=True, exist_ok=True)
    with open(_log_file, "a", encoding="utf-8"):
        pass
except Exception:
    _ENABLE_FILE_LOG = False

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "maxBytes": 1024 * 1024 * 10,  # 10MB
            "backupCount": 10,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

if not _ENABLE_FILE_LOG:
    LOGGING["handlers"].pop("file", None)

    def _remove_file_handler(handler_list):
        return [h for h in handler_list if h != "file"]

    LOGGING["root"]["handlers"] = _remove_file_handler(LOGGING["root"]["handlers"]) or [
        "console"
    ]

    for _cfg in LOGGING.get("loggers", {}).values():
        if "handlers" in _cfg:
            _cfg["handlers"] = _remove_file_handler(_cfg["handlers"]) or ["console"]
