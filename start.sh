#!/bin/sh

# Se a variável BUILD_MODE estiver definida, executa apenas tarefas de build
if [ "$BUILD_MODE" = "true" ]; then
    echo "=== MODO BUILD ==="
    pip install --upgrade pip
    pip install -r requirements.txt
    python3 manage.py collectstatic --noinput
    exit 0
fi

# === MODO RUNTIME (Start Command) ===
echo "=== MODO RUNTIME ==="

# Configurar permissões
python3 -c "
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO CURRENT_USER;')
        cursor.execute('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO CURRENT_USER;')
        cursor.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO CURRENT_USER;')
except: pass
"

# Migrações
python3 manage.py migrate --no-input

# Dados iniciais
if [ -f "dados_blog.json" ]; then
    python3 -c "
from django.core.management import call_command
from blog.models import Program
if Program.objects.count() == 0:
    call_command('loaddata', 'dados_blog.json')
"
fi

# Gunicorn
PORT=$(echo "$PORT" | sed 's/^0*//')
PORT=${PORT:-8000}
exec gunicorn sitio.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --log-level info --access-logfile - --error-logfile -