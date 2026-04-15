#!/bin/bash
# build.sh - Executado APENAS durante o build

echo "=== BUILD: Instalando dependências ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== BUILD: Configurando permissões do banco ==="
python3 -c "
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO CURRENT_USER;')
        cursor.execute('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO CURRENT_USER;')
        cursor.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO CURRENT_USER;')
        print('✅ Permissões configuradas')
except Exception as e:
    print(f'⚠️ Aviso: {e}')
"

echo "=== BUILD: Coletando arquivos estáticos ==="
python3 manage.py collectstatic --noinput

echo "=== BUILD: Concluído ==="