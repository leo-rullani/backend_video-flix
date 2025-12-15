"""
Django settings for the Videoflix backend.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Docker usually injects env vars via docker-compose env_file.
# This is a safe fallback for local runs.
load_dotenv(BASE_DIR / ".env")

ENV_FILE = os.environ.get("ENV_FILE", "").strip()
if ENV_FILE:
    load_dotenv(BASE_DIR / ENV_FILE, override=True)


def env_bool(key: str, default: bool = False) -> bool:
    """Read a boolean environment variable."""
    return os.environ.get(key, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(key: str, default: str = "") -> list[str]:
    """Read a comma-separated list environment variable."""
    raw = os.environ.get(key, default)
    return [x.strip() for x in raw.split(",") if x.strip()]


SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
DEBUG = env_bool("DEBUG", True)

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "127.0.0.1,localhost")

CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:4200,"
    "http://127.0.0.1:5500,"
    "http://localhost:5500,"
    "http://localhost:8000,"
    "http://127.0.0.1:8000",
)

# Frontend links inside emails (activation + password reset)
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://127.0.0.1:5500")
FRONTEND_ACTIVATION_PATH = os.environ.get(
    "FRONTEND_ACTIVATION_PATH",
    "/pages/auth/activate.html",
)
# IMPORTANT: This must point to the page where the user sets a NEW password (not "forgot_password.html")
FRONTEND_PASSWORD_RESET_PATH = os.environ.get(
    "FRONTEND_PASSWORD_RESET_PATH",
    "/pages/auth/confirm_password.html",
)

# Cookie security
COOKIE_SECURE = env_bool("COOKIE_SECURE", False)
COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "Lax")

CSRF_COOKIE_SECURE = COOKIE_SECURE
SESSION_COOKIE_SECURE = COOKIE_SECURE
CSRF_COOKIE_SAMESITE = COOKIE_SAMESITE
SESSION_COOKIE_SAMESITE = COOKIE_SAMESITE

# Email
# Teacher expects SMTP by default (can be overridden via .env if needed)
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")

EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)

# Avoid hanging forever if SMTP is misconfigured
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "10"))

# If SSL is enabled (usually port 465), TLS must be disabled
if EMAIL_USE_SSL:
    EMAIL_USE_TLS = False

# Fix common placeholder issue: DEFAULT_FROM_EMAIL=default_from_email
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "").strip()
if not DEFAULT_FROM_EMAIL or DEFAULT_FROM_EMAIL.lower() in {"default_from_email", "none"}:
    DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or "no-reply@example.com"

SERVER_EMAIL = os.environ.get("SERVER_EMAIL", DEFAULT_FROM_EMAIL)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_rq",
    "content.apps.ContentConfig",
    "auth.apps.AuthConfig",
    "import_export",
]

IMPORT_EXPORT_USE_TRANSACTIONS = True

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

INTERNAL_IPS: list[str] = ["127.0.0.1"]

if DEBUG:
    try:
        import debug_toolbar  # noqa: F401
        import socket

        INSTALLED_APPS += ["debug_toolbar"]
        MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE

        _, _, ips = socket.gethostbyname_ex(socket.gethostname())
        extra_ips: set[str] = set()
        for ip in ips:
            parts = ip.split(".")
            if len(parts) == 4:
                parts[-1] = "1"
                extra_ips.add(".".join(parts))
        INTERNAL_IPS = sorted(set(INTERNAL_IPS) | extra_ips)
    except Exception:
        INTERNAL_IPS = ["127.0.0.1"]

if DEBUG and "debug_toolbar" in INSTALLED_APPS:
    DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda request: True}

ROOT_URLCONF = "core.urls"

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

WSGI_APPLICATION = "core.wsgi.application"

# IMPORTANT: Docker defaults should use service names db / redis (not 127.0.0.1)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "videoflix_db"),
        "USER": os.environ.get("DB_USER", "videoflix_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "supersecretpassword"),
        "HOST": os.environ.get("DB_HOST", "db"),
        "PORT": int(os.environ.get("DB_PORT", "5432")),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.environ.get("REDIS_LOCATION", "redis://redis:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "KEY_PREFIX": "videoflix",
    }
}

RQ_QUEUES = {
    "default": {
        "HOST": os.environ.get("REDIS_HOST", "redis"),
        "PORT": int(os.environ.get("REDIS_PORT", "6379")),
        "DB": int(os.environ.get("REDIS_DB", "0")),
        "DEFAULT_TIMEOUT": 360,
        "REDIS_CLIENT_KWARGS": {},
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "auth.authentication.CookieJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=45),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://127.0.0.1:5500,"
    "http://localhost:5500,"
    "http://127.0.0.1:4200,"
    "http://localhost:4200",
)
CORS_ALLOW_CREDENTIALS = True