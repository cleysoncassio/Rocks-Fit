"""
WSGI config for sitio project.
"""
import os
from django.core.wsgi import get_wsgi_application

# Em servidores como Gunicorn, o padrão deve ser PRODUÇÃO
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings.production")

application = get_wsgi_application()
