from pathlib import Path

import environ
import sys


# -----------------------------------------------------------------------------
# Paths and environment
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env.read_env(BASE_DIR / ".env")

TESTING = "test" in sys.argv


# -----------------------------------------------------------------------------
# Core settings
# -----------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["127.0.0.1", "localhost", "testserver", "8000.frp.chatgqt.top"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=["http://8000.frp.chatgqt.top", "https://8000.frp.chatgqt.top"])


# -----------------------------------------------------------------------------
# Applications and middleware
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    "simpleui",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "tinymce",
    "apps.accounts",
    "apps.admin_portal",
    "apps.core",
    "apps.members",
    "apps.learning",
    "apps.reports",
    "apps.civic_feedbacks",
    "apps.problem_feedbacks",
    "apps.activities",
    "apps.elder_services",
    "apps.points",
    "apps.merchants",
    "apps.service_records",
    "apps.service_locations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"


# -----------------------------------------------------------------------------
# Templates and ASGI/WSGI
# -----------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DJANGO_DB_NAME", default="street"),
        "USER": env("DJANGO_DB_USER", default="street"),
        "PASSWORD": env("DJANGO_DB_PASSWORD", default="street"),
        "HOST": env("DJANGO_DB_HOST", default="127.0.0.1"),
        "PORT": env("DJANGO_DB_PORT", default="5432"),
    }
}


# -----------------------------------------------------------------------------
# Cache
# -----------------------------------------------------------------------------
if TESTING:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": env("DJANGO_REDIS_URL", default="redis://127.0.0.1:6379/0"),
        }
    }


# -----------------------------------------------------------------------------
# Authentication and localization
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = []
AUTH_USER_MODEL = "accounts.User"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True


# -----------------------------------------------------------------------------
# Static and media files
# -----------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "data" / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "data" / "media"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# -----------------------------------------------------------------------------
# Django defaults
# -----------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "street": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}


# -----------------------------------------------------------------------------
# Rate limiting
# -----------------------------------------------------------------------------
if TESTING:
    RATELIMIT_ENABLE = False
else:
    RATELIMIT_ENABLE = env.bool("RATELIMIT_ENABLE", default=True)


# -----------------------------------------------------------------------------
# Miniprogram and WeChat integration
# -----------------------------------------------------------------------------
ACCESS_TOKEN_SECRET = env("ACCESS_TOKEN_SECRET", default=SECRET_KEY)
ACCESS_TOKEN_EXPIRES_SECONDS = env.int("ACCESS_TOKEN_EXPIRES_SECONDS", default=7200)
WECHAT_MINIAPP_APPID = env("WECHAT_MINIAPP_APPID", default="")
WECHAT_MINIAPP_SECRET = env("WECHAT_MINIAPP_SECRET", default="")


# -----------------------------------------------------------------------------
# TinyMCE
# -----------------------------------------------------------------------------
TINYMCE_DEFAULT_CONFIG = {
    "height": 500,
    "menubar": "file edit view insert format tools table help",
    "plugins": "advlist autolink lists link image charmap preview anchor searchreplace visualblocks code fullscreen media table help wordcount",
    "toolbar": "undo redo | blocks | bold italic | alignleft aligncenter alignright | bullist numlist | image link media | code",
    "language": "zh_CN",
    "automatic_uploads": True,
    "images_upload_url": "/admin/tinymce/upload/image/",
    "file_picker_types": "image media",
    "file_picker_callback": "streetServiceTinymceFilePicker",
    "promotion": False,
    "branding": False,
}
TINYMCE_EXTRA_MEDIA = {
    "js": ["admin/js/tinymce_upload.js"],
}


# -----------------------------------------------------------------------------
# SimpleUI admin
# -----------------------------------------------------------------------------
SIMPLEUI_HOME_INFO = False
SIMPLEUI_ANALYSIS = False
SIMPLEUI_HOME_ACTION = False
SIMPLEUI_CONFIG = {
    "system_keep": False,
    "menus": [
        {
            "name": "用户管理",
            "icon": "fas fa-users",
            "permission": "members.view_member",
            "models": [
                {"name": "用户档案", "icon": "fas fa-user", "url": "/admin/members/member/", "permission": "members.view_member"},
            ],
        },
        {
            "name": "学习宣传",
            "icon": "fas fa-book-open",
            "permission": "learning.view_learningcontent",
            "models": [
                {"name": "学习内容", "icon": "fas fa-book", "url": "/admin/learning/learningcontent/", "permission": "learning.view_learningcontent"},
                {"name": "学习记录", "icon": "fas fa-clipboard-list", "url": "/admin/learning/learningrecord/", "permission": "learning.view_learningrecord"},
            ],
        },
        {
            "name": "随手上报",
            "icon": "fas fa-flag",
            "permission": "reports.view_report",
            "models": [
                {"name": "上报记录", "icon": "fas fa-file-lines", "url": "/admin/reports/report/", "permission": "reports.view_report"},
                {"name": "社情民意", "icon": "fas fa-comments", "url": "/admin/civic_feedbacks/civicfeedback/", "permission": "civic_feedbacks.view_civicfeedback"},
                {"name": "问题反馈", "icon": "fas fa-circle-question", "url": "/admin/problem_feedbacks/problemfeedback/", "permission": "problem_feedbacks.view_problemfeedback"},
            ],
        },
        {
            "name": "活动管理",
            "icon": "fas fa-calendar-check",
            "permission": "activities.view_activity",
            "models": [
                {"name": "活动", "icon": "fas fa-calendar-day", "url": "/admin/activities/activity/", "permission": "activities.view_activity"},
                {"name": "报名记录", "icon": "fas fa-user-plus", "url": "/admin/activities/activitysignup/", "permission": "activities.view_activitysignup"},
                {"name": "签到记录", "icon": "fas fa-clipboard-check", "url": "/admin/activities/activitycheckin/", "permission": "activities.view_activitycheckin"},
            ],
        },
        {
            "name": "助老服务",
            "icon": "fas fa-hand-holding-heart",
            "permission": "elder_services.view_elderservicetask",
            "models": [
                {"name": "服务任务", "icon": "fas fa-list-check", "url": "/admin/elder_services/elderservicetask/", "permission": "elder_services.view_elderservicetask"},
                {"name": "结对帮扶关系", "icon": "fas fa-user-friends", "url": "/admin/elder_services/eldercarerelation/", "permission": "elder_services.view_eldercarerelation"},
                {"name": "服务反馈", "icon": "fas fa-comment-dots", "url": "/admin/elder_services/elderservicefeedback/", "permission": "elder_services.view_elderservicefeedback"},
            ],
        },
        {
            "name": "积分与商户",
            "icon": "fas fa-store",
            "permission": "points.view_pointaccount",
            "models": [
                {"name": "积分账户", "icon": "fas fa-wallet", "url": "/admin/points/pointaccount/", "permission": "points.view_pointaccount"},
                {"name": "积分流水", "icon": "fas fa-receipt", "url": "/admin/points/pointrecord/", "permission": "points.view_pointrecord"},
                {"name": "人工调分", "icon": "fas fa-pen-to-square", "url": "/admin/points/manualpointadjustment/", "permission": "points.view_manualpointadjustment"},
                {"name": "积分兑换比例", "icon": "fas fa-scale-balanced", "url": "/admin/points/pointexchangerule/", "permission": "points.view_pointexchangerule"},
                {"name": "商户", "icon": "fas fa-shop", "url": "/admin/merchants/merchant/", "permission": "merchants.view_merchant"},
                {"name": "商户结算", "icon": "fas fa-file-invoice-dollar", "url": "/admin/merchants/merchantsettlement/", "permission": "merchants.view_merchantsettlement"},
            ],
        },
        {
            "name": "后台账号",
            "icon": "fas fa-user-shield",
            "permission": "accounts.view_user",
            "models": [
                {"name": "后台账号", "icon": "fas fa-user-shield", "url": "/admin/accounts/user/", "permission": "accounts.view_user"},
            ],
        },
    ],
    "dynamic": False,
}
