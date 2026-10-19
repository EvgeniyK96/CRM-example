from decimal import Decimal
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    LANGUAGE_CODE=(str, "ru"),
    TIME_ZONE=(str, "Asia/Almaty"),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "djoser",
    "drf_yasg",
    "corsheaders",
    "django_filters",
    "core",
    "apps.accounts",
    "apps.hr",
    "apps.catalog",
    "apps.recipes",
    "apps.warehouse",
    "apps.purchasing",
    "apps.sales",
    "apps.production",
    "apps.accounting",
    "apps.payroll",
    "apps.reports",
    "apps.activity",
    # LOCAL_APPS_MARKER — не удаляй эту строку, она используется create_app.py
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.current_user.CurrentUserMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

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

WSGI_APPLICATION = "core.wsgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = env("LANGUAGE_CODE")
TIME_ZONE = env("TIME_ZONE")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / env("STATIC_ROOT", default="staticfiles")

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / env("MEDIA_ROOT", default="media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.DefaultPagination",
    "EXCEPTION_HANDLER": "core.exceptions.exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "core.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

SIMPLE_JWT = {
    "AUTH_HEADER_TYPES": ("Bearer",),
}

DJOSER = {
    "SERIALIZERS": {
        "user": "apps.accounts.serializers.UserSerializer",
        "current_user": "apps.accounts.serializers.UserSerializer",
    },
}

AUTH_USER_MODEL = "accounts.User"

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:5173", "http://127.0.0.1:5173"])

# За прокси хостинга (Vercel и т. п.) запрос приходит по HTTP, а исходный протокол — в X-Forwarded-Proto.
# Без этого Django считает запрос небезопасным, и вход в админку падает на проверке CSRF (Origin https ≠ http).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Домены, с которых разрешены формы с CSRF (админка): https://crm-backend.vercel.app и т. п.
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
        }
    },
    "USE_SESSION_AUTH": False,
}

# Зарплата (учебные значения): стандартный вычет при расчёте ИПН и среднее число календарных дней в месяце
PAYROLL_STANDARD_DEDUCTION = Decimal(env.str("PAYROLL_STANDARD_DEDUCTION", default="60550"))  # ≈ 14 МРП
PAYROLL_AVG_MONTH_DAYS = Decimal(env.str("PAYROLL_AVG_MONTH_DAYS", default="29.3"))

# Админка (тема Jazzmin)
JAZZMIN_SETTINGS = {
    "site_title": "CRM Фабрика",
    "site_header": "CRM Фабрика",
    "site_brand": "CRM Фабрика",
    "welcome_sign": "Администрирование CRM кондитерской фабрики",
    "copyright": "Учебный проект",
}

# Продакшен (DEBUG=False): куки сессии и CSRF только по HTTPS.
# Редирект на HTTPS и HSTS на доменах *.vercel.app делает сама платформа.
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
