import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings.development")
django.setup()

from django.test import RequestFactory
from blog.views import crm_whatsapp_campanha
from blog.models import User

factory = RequestFactory()
request = factory.post('/crm/campanha-whatsapp/', {'audience': 'TODOS', 'message': 'Teste'})
user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User(username='test', is_superuser=True)
request.user = user

from django.contrib.messages.storage.fallback import FallbackStorage
setattr(request, 'session', 'session')
messages = FallbackStorage(request)
setattr(request, '_messages', messages)

try:
    response = crm_whatsapp_campanha(request)
    print("Response status:", response.status_code)
except Exception as e:
    import traceback
    traceback.print_exc()
