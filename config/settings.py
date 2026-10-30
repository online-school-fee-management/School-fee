import os
from pathlib import Path

from django.contrib.messages import constants as message_constants

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Mode
# If SECRET_KEY is set in the environment we are in PRODUCTION (server).
# Without it (your own PC) everything works exactly like before:
# DEBUG on, SQLite, abc.localhost:8000.
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "")
PRODUCTION = bool(SECRET_KEY)
if not PRODUCTION:
    SECRET_KEY = "dev-only-change-me-before-production"

DEBUG = env_bool("DEBUG", default=not PRODUCTION)

# Tenant (school) is identified by subdomain: abc.<BASE_DOMAIN> -> school "abc"
# Production example: BASE_DOMAIN=scholodia.online
BASE_DOMAIN = os.environ.get("BASE_DOMAIN", "localhost")
ALLOWED_HOSTS = [BASE_DOMAIN, f".{BASE_DOMAIN}"]
if not PRODUCTION or DEBUG:
    ALLOWED_HOSTS += ["localhost", ".localhost", "127.0.0.1"]

# ---------------------------------------------------------------------------
# HTTPS
# Keep USE_HTTPS unset/0 until the SSL certificate is installed on the server.
# Turning it on while the site is still plain HTTP would break logins
# (secure cookies are not sent over HTTP).
# ---------------------------------------------------------------------------
USE_HTTPS = env_bool("USE_HTTPS", default=False)

CSRF_TRUSTED_ORIGINS = []
if PRODUCTION:
    _scheme = "https" if USE_HTTPS else "http"
    CSRF_TRUSTED_ORIGINS = [f"{_scheme}://{BASE_DOMAIN}", f"{_scheme}://*.{BASE_DOMAIN}"]

if PRODUCTION and USE_HTTPS:
    # Nginx terminates SSL and tells Django the original scheme.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "tenants",
    "accounts",
    "academics",
    "fees.apps.FeesConfig",
    "payments",
    "accounting",
    "dashboard",
    "portal",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "tenants.middleware.TenantMiddleware",
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
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# DB_NAME set  -> PostgreSQL (production)
# DB_NAME unset -> SQLite (your PC); DB_PATH can move the file outside the repo
# ---------------------------------------------------------------------------
if os.environ.get("DB_NAME"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["DB_NAME"],
            "USER": os.environ.get("DB_USER", "postgres"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("DB_PATH", BASE_DIR / "db.sqlite3"),
        }
    }

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["accounts.backends.SchoolBackend"]
# Username is unique per school (not globally), so Django warns about it.
SILENCED_SYSTEM_CHECKS = ["auth.W004"]

LOGIN_URL = "/login/"

# Initial password given to every new student account (admin can reset it).
# Override with the DEFAULT_STUDENT_PASSWORD environment variable.
DEFAULT_STUDENT_PASSWORD = os.environ.get("DEFAULT_STUDENT_PASSWORD", "12345678")

# Make Django's "error" messages use Bootstrap's "danger" colour.
MESSAGE_TAGS = {message_constants.ERROR: "danger"}

LANGUAGE_CODE = "en"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

# Static files: `python manage.py collectstatic` copies everything to
# STATIC_ROOT, and Nginx serves /static/ from there.
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Uploaded files (gallery etc.): Nginx serves /media/ from MEDIA_ROOT.
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# With DEBUG off Django hides tracebacks. Send errors to the console so they
# show up in `journalctl -u fee-app`.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
}
