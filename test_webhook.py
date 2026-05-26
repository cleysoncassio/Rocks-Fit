import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings.development")
django.setup()

from django.test import RequestFactory
from blog.views import webhook_evolution_api

factory = RequestFactory()
payload = {
    "event": "messages.upsert",
    "data": {
        "messages": [
            {
                "key": {
                    "remoteJid": "5584999991111@s.whatsapp.net",
                    "fromMe": False
                },
                "message": {
                    "conversation": "Olá, meu CPF é 123.456.789-01"
                }
            }
        ]
    }
}
request = factory.post('/api/evolution-webhook/', json.dumps(payload), content_type='application/json')
request.headers = {'apikey': ''}

try:
    response = webhook_evolution_api(request)
    print("Response status:", response.status_code)
except Exception as e:
    import traceback
    traceback.print_exc()
