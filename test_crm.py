import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings.development")
django.setup()

from django.test import RequestFactory
from blog.views import crm_dashboard
from django.contrib.auth.models import User

factory = RequestFactory()
request = factory.get('/crm/')
user = User.objects.filter(is_superuser=True).first()
request.user = user

try:
    response = crm_dashboard(request)
    print("Response status:", response.status_code)
except Exception as e:
    import traceback
    traceback.print_exc()
