from pathlib import Path

from django.contrib.messages import constants as message_constants

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "dev-only-change-me-before-production"
DEBUG = True

# Tenant (school) is identified by subdomain: abc.localhost:8000 -> school "abc"
# In production set this to your real domain, e.g. "feeplatform.com"
BASE_DOMAIN = "localhost"
ALLOWED_HOSTS = [".localhost", "localhost", "127.0.0.1"]

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

# SQLite for development. Switch to PostgreSQL for production:
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": "school_fee",
#         "USER": "postgres",
#         "PASSWORD": "your-password",
#         "HOST": "localhost",
#         "PORT": "5432",
#     }
# }
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["accounts.backends.SchoolBackend"]
# Username is unique per school (not globally), so Django warns about it.
SILENCED_SYSTEM_CHECKS = ["auth.W004"]

LOGIN_URL = "/login/"

# Initial password given to every new student account (admin can reset it).
DEFAULT_STUDENT_PASSWORD = "12345678"

# Make Django's "error" messages use Bootstrap's "danger" colour.
MESSAGE_TAGS = {message_constants.ERROR: "danger"}

LANGUAGE_CODE = "en"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
