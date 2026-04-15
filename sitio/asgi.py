"""
ASGI config for sitio project.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings.production")

application = get_wsgi_application()
