import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings.development")
django.setup()

from django.test import RequestFactory
from blog.views import home

factory = RequestFactory()
request = factory.get('/')

try:
    response = home(request)
    print("Response status:", response.status_code)
except Exception as e:
    import traceback
    traceback.print_exc()
