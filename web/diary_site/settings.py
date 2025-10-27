from pathlib import Path
import os
import sys

# Ensure repository root is on sys.path so `common` is importable
BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common.database.db_config import get_db_config

cfg = get_db_config()

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-key")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h for h in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "bootstrap5",
    "diary",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
]

ROOT_URLCONF = "diary_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [],
        },
    }
]

WSGI_APPLICATION = "diary_site.wsgi.application"
ASGI_APPLICATION = "diary_site.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": cfg.database,
        "USER": cfg.user,
        "PASSWORD": cfg.password,
        "HOST": cfg.host,
        "PORT": cfg.port,
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"sslmode": cfg.sslmode},
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"


