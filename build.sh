#!/bin/bash
# build.sh — Executado durante o build na Hostman (PRODUÇÃO)
export DJANGO_SETTINGS_MODULE=sitio.settings.production

pip install --upgrade pip
pip install -r requirements.txt

python3 manage.py collectstatic --noinput
python3 manage.py migrate --noinput

# Carregar dados iniciais (se existir e banco estiver vazio)
if [ -f "dados_blog.json" ]; then
    python3 -c "
import django; django.setup()
from blog.models import Program
if Program.objects.count() == 0:
    from django.core.management import call_command
    call_command('loaddata', 'dados_blog.json')
    print('Dados iniciais carregados.')
else:
    print('Dados ja existem — pulando loaddata.')
"
fi