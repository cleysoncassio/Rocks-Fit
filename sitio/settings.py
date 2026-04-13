import os
from pathlib import Path

import dj_database_url
from decouple import Csv, config
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/
load_dotenv()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY", default="django-insecure-placeholder")
STONE_SECRET_KEY = config("STONE_SECRET_KEY", default="sk_test_placeholder_sua_chave")

# ALTERADO: padrão seguro é False (produção), ative True apenas no desenvolvimento local
DEBUG = config("DEBUG", default=False, cast=bool)

# Pega o que está no painel da Hostman (tenta os dois nomes padrão)
env_hosts = config("ALLOWED_HOSTS", default=config("DJANGO_ALLOWED_HOSTS", default=""))

# ALLOWED_HOSTS corrigido e simplificado
if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    # Domínios base vindos do painel da Hostman
    if env_hosts:
        ALLOWED_HOSTS = [h.strip() for h in env_hosts.split(",") if h.strip()]
    else:
        # Fallback seguro - ATUALIZE SE SEUS DOMÍNIOS MUDAREM
        ALLOWED_HOSTS = [
            "academiarocksfit.com.br",
            "www.academiarocksfit.com.br",
            ".hostman.site",
            "195.133.93.36",
        ]
    
    # IPs para health checks da Hostman
    for ip in ["127.0.0.1", "localhost", "192.168.0.4"]:
        if ip not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(ip)

# IMPORTANTE: Para o domínio profissional funcionar com formulários (Login da Academia)
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://academiarocksfit.com.br,https://www.academiarocksfit.com.br,https://*.hostman.site",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

# --- CONFIGURAÇÕES DE SEGURANÇA (Ajustadas para Desenvolvimento/Produção) ---
if not DEBUG:
    # Seguranca HTTPS forçada em Producao
    import sys
    is_runserver = 'runserver' in sys.argv
    
    # Redireciona para HTTPS apenas se não for runserver local
    SECURE_SSL_REDIRECT = not is_runserver
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    
    # HSTS (Apenas em produção real, não no runserver)
    if not is_runserver:
        SECURE_HSTS_SECONDS = 31536000  # 1 ano
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True
    else:
        SECURE_HSTS_SECONDS = 0
        SECURE_HSTS_INCLUDE_SUBDOMAINS = False
        SECURE_HSTS_PRELOAD = False

    SESSION_COOKIE_SECURE = not is_runserver
    CSRF_COOKIE_SECURE = not is_runserver
    
    # Outros cabecalhos
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    
    # Política de Referer
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    
    # Impedir que o site seja embutido em iframes (clickjacking)
    X_FRAME_OPTIONS = 'DENY'
else:
    # --- CONFIGURAÇÕES ESPECÍFICAS PARA DESENVOLVIMENTO LOCAL ---
    # Desabilita redirecionamento SSL (o servidor de desenvolvimento não suporta HTTPS)
    SECURE_SSL_REDIRECT = False
    
    # Permite cookies HTTP em desenvolvimento (para testes locais)
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    
    # Desabilita cabeçalhos de segurança que não se aplicam ao desenvolvimento
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SECURE_BROWSER_XSS_FILTER = False
    SECURE_CONTENT_TYPE_NOSNIFF = False
    
    # Configuração para evitar problemas com webhooks que tentam HTTPS
    # Isso resolve o erro "You're accessing the development server over HTTPS"
    SECURE_PROXY_SSL_HEADER = None

# Application definition
INSTALLED_APPS = [
    "blog",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "sass_processor",
    "ordered_model",
    "axes",
    "csp",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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

STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# URLs do projeto
ROOT_URLCONF = "sitio.urls"

INTERNAL_IPS = config("INTERNAL_IPS", cast=Csv(), default="127.0.0.1")

GS_BUCKET_NAME = "<your-bucket-name>"

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

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": config(
        "DATABASE_URL",
        default="sqlite:///" + os.path.join(BASE_DIR, "db.sqlite3"),
        cast=dj_database_url.parse,
    )
}

# PARA ACESSAR O PGADMIN WEB:
# pgadmin4
# http://http://127.0.0.1:5050


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "pt-br"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "sass_processor.finders.CssFinder",
]

SASS_PROCESSOR_ROOT = os.path.join(BASE_DIR, "static")

STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "blog/templates/base/static")]

# WhiteNoise storage to serve compressed and versioned static files
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # Usamos ManifestStaticFilesStorage em vez de CompressedManifestStaticFilesStorage
        # para evitar o "PermissionError: [Errno 13]" ao tentar criar arquivos .gz na Hostman.
        "BACKEND": "whitenoise.storage.ManifestStaticFilesStorage",
    },
}

# Arquivos de mídia
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Configurações de email (exemplo usando console backend)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Security audit for deployment
# python manage.py check --deploy

WHITENOISE_MANIFEST_STRICT = False

# Configurações do Controle de Acesso (Catraca)
CATRACA_SYNC_TOKEN = "rocksfit@2024"

# Django-Axes (Protecao Brute Force)
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AXES_FAILURE_LIMIT = 5  # Bloqueia após 5 tentativas
AXES_COOLOFF_TIME = 1   # Bloqueio dura 1 hora
AXES_LOCKOUT_TEMPLATE = "base/fake_admin.html"  # Usa o honeypot como tela de bloqueio
AXES_RESET_ON_SUCCESS = True


# Configuração atualizada do Django-CSP (Versão 4.0+)
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

# Ratelimit (Geral)
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_CACHE_PREFIX = 'ratelimit'