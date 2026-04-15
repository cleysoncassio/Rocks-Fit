"""
Configurações de PRODUÇÃO.
Usado na Hostman (Gunicorn + PostgreSQL).

Para ativar: DJANGO_SETTINGS_MODULE=sitio.settings.production
"""
import dj_database_url

from decouple import config

from .base import *  # noqa: F401,F403

# ============================================================
#  PRODUÇÃO — DEBUG DESATIVADO
# ============================================================
DEBUG = False


# ============================================================
#  HOSTS PERMITIDOS
# ============================================================
_env_hosts = config("ALLOWED_HOSTS", default="")

if _env_hosts:
    ALLOWED_HOSTS = [h.strip() for h in _env_hosts.split(",") if h.strip()]
else:
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


# ============================================================
#  CSRF
# ============================================================
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://academiarocksfit.com.br,https://www.academiarocksfit.com.br,https://*.hostman.site",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)


# ============================================================
#  BANCO DE DADOS — PostgreSQL (via DATABASE_URL)
# ============================================================
DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL", default=""),
        conn_max_age=600,
    )
}


# ============================================================
#  SEGURANÇA HTTPS — tudo ativado
# ============================================================
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# HSTS (1 ano)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies seguros
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Cabeçalhos de segurança
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'


# ============================================================
#  E-MAIL (configurar quando necessário)
# ============================================================
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
