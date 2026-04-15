"""
Configurações de DESENVOLVIMENTO.
Usado automaticamente ao rodar localmente (manage.py runserver).

Para ativar: DJANGO_SETTINGS_MODULE=sitio.settings.development
"""
from .base import *  # noqa: F401,F403

# ============================================================
#  DESENVOLVIMENTO — DEBUG ATIVADO
# ============================================================
DEBUG = True

ALLOWED_HOSTS = ["*"]

# CSRF — trustar localhost para formulários
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


# ============================================================
#  BANCO DE DADOS — SQLite local (leve, sem dependências)
# ============================================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ============================================================
#  SEGURANÇA — tudo desabilitado para dev
# ============================================================
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_PROXY_SSL_HEADER = None


# ============================================================
#  E-MAIL — Console (apenas exibe no terminal)
# ============================================================
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
