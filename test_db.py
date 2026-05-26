import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings.development")
django.setup()

from blog.models import Aluno
alunos = Aluno.objects.exclude(whatsapp__isnull=True).exclude(whatsapp__exact='')
print("Total alunos:", alunos.count())
for a in alunos:
    print(a.id, a.whatsapp)
