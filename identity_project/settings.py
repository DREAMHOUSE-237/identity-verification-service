import os
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY    = os.environ.get("SECRET_KEY", "identity-dev-secret")
DEBUG         = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

# ── Spring Cloud Config ───────────────────────────────────────────
CONFIG_SERVER_URL = os.environ.get("CONFIG_SERVER_URL", "http://192.168.172.22:8080")
APP_NAME          = os.environ.get("APP_NAME", "IDENTITY-SERVICE")
PROFILE           = os.environ.get("PROFILE", "dev")

# ── Eureka ────────────────────────────────────────────────────────
EUREKA_URL              = os.environ.get("EUREKA_URL", "http://ec2-16-171-142-15.eu-north-1.compute.amazonaws.com:8761")
EUREKA_REG_MAX_ATTEMPTS = int(os.environ.get("EUREKA_REG_MAX_ATTEMPTS", "6"))
EUREKA_REG_BASE_WAIT    = float(os.environ.get("EUREKA_REG_BASE_WAIT", "2.0"))

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'identity_app.apps.IdentityAppConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'identity_project.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]

WSGI_APPLICATION = 'identity_project.wsgi.application'

# ── Database ──────────────────────────────────────────────────────
# CONN_MAX_AGE=60 activates Django connection pooling.
# Without it Django opens+closes a MySQL connection on every HTTP request.
# With 60s the connection is reused → less memory and network latency.
if os.environ.get("DJANGO_ENV") == "production":
    DATABASES = {
        'default': {
            'ENGINE':       'django.db.backends.mysql',
            'NAME':         os.environ.get("MYSQL_DATABASE", "identity_db"),
            'USER':         os.environ.get("MYSQL_USER",     "identity_user"),
            'PASSWORD':     os.environ.get("MYSQL_PASSWORD", "ebate"),
            'HOST':         os.environ.get("MYSQL_HOST",     "127.0.0.1"),
            'PORT':         os.environ.get("MYSQL_PORT",     "3306"),
            'CONN_MAX_AGE': int(os.environ.get("DB_CONN_MAX_AGE", "60")),
            'OPTIONS':      {'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                             'connect_timeout': 10},
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

if 'test' in sys.argv:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}

# ── Static & Media ────────────────────────────────────────────────
STATIC_URL = 'static/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL  = '/media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE     = 'Africa/Douala'
USE_I18N      = True
USE_TZ        = True

# ── DRF ──────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ── RabbitMQ ──────────────────────────────────────────────────────
RABBITMQ_URL = os.environ.get(
    "RABBITMQ_URL",
    "amqp://dreamhouse:dreamhouse@192.168.172.81:5672/%2f"
)

# ── Tesseract ─────────────────────────────────────────────────────
# Override if tesseract is not in PATH on your system
# TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "/usr/bin/tesseract")

# ── Test flag (read by apps.py to skip background threads) ────────
TESTING = "test" in sys.argv

# ── Logging ───────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '[{levelname}] {name}: {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'identity_app': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
