import os
import django
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings.development")
django.setup()

from blog.models import Aluno

count = Aluno.objects.count()
print(f"Total de alunos no banco local (development): {count}")

# Check production too if possible
os.environ["DJANGO_SETTINGS_MODULE"] = "sitio.settings.production"
# Reload django? Actually it might be tricky.
print(f"DJANGO_SETTINGS_MODULE is now {os.environ['DJANGO_SETTINGS_MODULE']}")
