"""
Configurações de PRODUÇÃO.
Ativado na Hostman (academiarocksfit.com.br).
"""
import dj_database_url
from decouple import config
from .base import *

# Configurações de segurança: DEBUG deve ser False em produção para segurança e performance
DEBUG = config("DEBUG", default=False, cast=bool)

# Hosts configurados para produção - Restrito aos domínios oficiais
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="academiarocksfit.com.br,www.academiarocksfit.com.br", cast=lambda v: [s.strip() for s in v.split(",") if s.strip()])

# Adiciona fallbacks e IPs necessários para funcionamento/health checks
for h in ["academiarocksfit.com.br", "www.academiarocksfit.com.br", ".hostman.site", "127.0.0.1", "localhost"]:
    if h not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(h)

# IPs específicos conhecidos da infraestrutura
for ip in ["195.133.93.36", "192.168.0.4"]:
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

# Segurança HTTPS: Desativado por padrão no código (recomendado ativar via variável de ambiente na Hostman)
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
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

# Email backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Configuração de Logs Padrão para Produção (Limpo e Eficiente)
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

# Configuração do Cloudinary (Armazenamento de Imagens Persistente)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config("CLOUDINARY_CLOUD_NAME", default="dcpmp0hjf"),
    'API_KEY': config("CLOUDINARY_API_KEY", default="973228675879414"),
    'API_SECRET': config("CLOUDINARY_API_SECRET", default="Ggc4LL8P_3FZggiJdu6u4DPjG_A"),
}

# Configuração de Storage de Produção
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "cloudinary_storage.storage.StaticCloudinaryStorage",
    },
}

# Configurações Legado (Necessárias para compatibilidade de scripts de build na Hostman)
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
STATICFILES_STORAGE = 'cloudinary_storage.storage.StaticCloudinaryStorage'
