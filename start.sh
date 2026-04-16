#!/bin/sh
# start.sh — Executado pela Hostman para iniciar o serviço (PRODUÇÃO)
export DJANGO_SETTINGS_MODULE=sitio.settings.production

echo "=== ROCKS-FIT: INICIANDO PRODUÇÃO ==="

# Configurar permissões do banco
python3 -c "
import django; django.setup()
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO CURRENT_USER;')
        cursor.execute('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO CURRENT_USER;')
        cursor.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO CURRENT_USER;')
except: pass
"

# Migrações pendentes
python3 manage.py migrate --no-input

# Dados iniciais (somente se vazio)
if [ -f "dados_blog.json" ]; then
    python3 -c "
import django; django.setup()
from blog.models import Program
if Program.objects.count() == 0:
    from django.core.management import call_command
    call_command('loaddata', 'dados_blog.json')
"
fi

# Gunicorn
PORT=$(echo "$PORT" | sed 's/^0*//')
PORT=${PORT:-800}
exec gunicorn sitio.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --log-level info --access-logfile - --error-logfile -