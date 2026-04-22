
"""
Configurações de PRODUÇÃO.
Ativado na Hostman (academiarocksfit.com.br).
"""
import dj_database_url
from decouple import config
from .base import *

# Configurações de segurança: DEBUG deve ser False em produção
DEBUG = config("DEBUG", default=False, cast=bool)

# ============================================
# ALLOWED_HOSTS CORRIGIDO - NÃO usar '*' em produção!
# ============================================
# Domínios permitidos
ALLOWED_HOSTS = [
    "academiarocksfit.com.br",
    "www.academiarocksfit.com.br",
    ".hostman.site",  # Domínio interno da Hostman
    "195.133.93.36",  # IP público
]

# Adicionar IPs internos da Hostman para health check
for ip in ["127.0.0.1", "localhost", "192.168.0.4", "172.18.0.3", "172.18.0.4", "172.18.0.7"]:
    if ip not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(ip)

# CSRF Trust
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="https://academiarocksfit.com.br,https://www.academiarocksfit.com.br,https://*.hostman.site,http://*.hostman.site",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)

# Banco de Dados PostgreSQL
DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL", default=""),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ============================================
# FUNÇÃO PARA CONCEDER PERMISSÕES (executa na inicialização)
# ============================================
def grant_db_permissions():
    """Concede permissões no PostgreSQL para o usuário atual"""
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO CURRENT_USER;")
            cursor.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO CURRENT_USER;")
            cursor.execute("GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO CURRENT_USER;")
            cursor.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO CURRENT_USER;")
            cursor.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO CURRENT_USER;")
            print("✅ Permissões do banco concedidas com sucesso")
            return True
    except Exception as e:
        print(f"⚠️ Aviso ao conceder permissões: {e}")
        return False

# Executar concessão de permissões (tenta, mas não quebra se falhar)
try:
    grant_db_permissions()
except Exception as e:
    print(f"⚠️ Erro na concessão de permissões: {e}")

# Segurança HTTPS
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

# Email backend (configurar depois)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Logging
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


# STORAGES - Cloudinary para media, Cloudinary para estáticos (conforme solicitado)
STATICFILES_STORAGE = 'cloudinary_storage.storage.StaticCloudinaryStorage'

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "cloudinary_storage.storage.StaticCloudinaryStorage",
    },
}

# Django-Axes (reativar após permissões funcionarem)
AXES_ENABLED = False  # Mantenha False até resolver as permissões
AXES_BEHIND_REVERSE_PROXY = True

# Ratelimit
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'