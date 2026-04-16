"""
Configurações BASE compartilhadas entre todos os ambientes.
Não use este arquivo diretamente — use development.py ou production.py.
"""
import os
from pathlib import Path
from decouple import Csv, config
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# Agora BASE_DIR aponta para a raiz do projeto (2 níveis acima: settings/ → sitio/ → projeto/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Carrega .env da raiz do projeto para variáveis locais
load_dotenv(os.path.join(BASE_DIR, ".env"))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY", default="django-insecure-placeholder")
STONE_SECRET_KEY = config("STONE_SECRET_KEY", default="sk_test_placeholder_sua_chave")

# Application definition
INSTALLED_APPS = [
    "blog",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "cloudinary_storage",
    "django.contrib.staticfiles",
    "cloudinary",
    "sass_processor",
    "ordered_model",
    "axes",
    "csp",
    "corsheaders",
    "rest_framework",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "csp.middleware.CSPMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "sitio.urls"

INTERNAL_IPS = config("INTERNAL_IPS", cast=Csv(), default="127.0.0.1")

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "blog.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "sitio.wsgi.application"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "blog/templates/base/static")]

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "sass_processor.finders.CssFinder",
]

SASS_PROCESSOR_ROOT = os.path.join(BASE_DIR, "static")

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.ManifestStaticFilesStorage",
    },
}

WHITENOISE_MANIFEST_STRICT = False

# Arquivos de mídia
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Configurações do Controle de Acesso (Catraca)
CATRACA_SYNC_TOKEN = "rocksfit@2024"

# Django-Axes (Proteção Brute Force)
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_LOCKOUT_TEMPLATE = "base/fake_admin.html"
AXES_RESET_ON_SUCCESS = True

# Configuração do Django-CSP
CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': ("'self'",),
        'font-src': ("'self'", 'https://fonts.gstatic.com', 'https://cdnjs.cloudflare.com'),
        'frame-src': ("'self'", 'https://www.googletagmanager.com', 'https://www.google.com'),
        'img-src': ("'self'", 'data:', 'https://maps.google.com', 'https://www.googletagmanager.com'),
        'script-src': ("'self'", "'unsafe-inline'", 'https://www.googletagmanager.com'),
        'style-src': ("'self'", "'unsafe-inline'", 'https://fonts.googleapis.com', 'https://cdnjs.cloudflare.com'),
        'style-src-attr': ("'self'", "'unsafe-inline'")
    }
}

# Ratelimit
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_CACHE_PREFIX = 'ratelimit'

# CORS Settings
CORS_ALLOW_ALL_ORIGINS = True  # Para desenvolvimento do App do Aluno
