"""
Configurações de DESENVOLVIMENTO.
Padrão para rodar localmente.
"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Banco de dados SQLite para desenvolvimento
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Desabilita configurações de segurança para facilitar o desenvolvimento local
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_PROXY_SSL_HEADER = None

# E-mail no console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Origens confiáveis para CSRF em desenvolvimento
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Sobrescreve STORAGES para desenvolvimento (evita o ManifestStaticFilesStorage do WhiteNoise que exige collectstatic)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Fallbacks legados para pacotes que não suportam STORAGES (como django-cloudinary-storage)
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
