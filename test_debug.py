import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings.development")
django.setup()
from blog.models import GymSetting
gs = GymSetting.objects.first()
print(f"URL: {gs.evolution_api_url if gs else 'N/A'}")
print(f"Key: {gs.evolution_api_key if gs else 'N/A'}")
print(f"Instance: {gs.evolution_instance_name if gs else 'N/A'}")
