"""
Configurações de PRODUÇÃO.
Ativado na Hostman (academiarocksfit.com.br).
"""
import dj_database_url
from decouple import config
from .base import *

# Configurações de segurança: DEBUG deve ser False em produção
DEBUG = config("DEBUG", default=False, cast=bool)

# Hosts configurados para produção
env_hosts = config("ALLOWED_HOSTS", default="")
if env_hosts:
    ALLOWED_HOSTS = [h.strip() for h in env_hosts.split(",") if h.strip()]
else:
    # Fallback para os domínios conhecidos
    ALLOWED_HOSTS = [
        "academiarocksfit.com.br",
        "www.academiarocksfit.com.br",
        ".hostman.site",
        "195.133.93.36",
    ]

# IPs para health checks e acesso interno
for ip in ["127.0.0.1", "localhost", "192.168.0.4"]:
    if ip not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(ip)

# CSRF Trust
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://academiarocksfit.com.br,https://www.academiarocksfit.com.br,https://*.hostman.site",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

# Banco de Dados PostgreSQL (DATABASE_URL fornecido pela Hostman)
DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL", default=""),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Segurança HTTPS total em Produção
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# HSTS
SECURE_HSTS_SECONDS = 31536000  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies Seguros
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Outros cabeçalhos de segurança
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
X_FRAME_OPTIONS = 'DENY'

# Email backend (Pode ser alterado para SMTP conforme necessário)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Forçar erros para o console do Hostman
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
