#!/bin/sh
# Script de inicialização Ultrarrobusto para Hostman

echo "--- INICIANDO APLICAÇÃO ---"

# 1. Diagnóstico básico
echo "Python: $(python3 -V)"
echo "Diretório atual: $(pwd)"

# 2. Configurar permissões do banco (ignora erros)
echo "Configurando permissões do banco..."
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

# 3. Carregar dados iniciais (se existir e se estiver vazio)
if [ -f "dados_blog.json" ]; then
    echo "Verificando dados iniciais..."
    # Só carrega se as tabelas estiverem vazias
    python3 -c "
from django.core.management import call_command
from blog.models import Program
if Program.objects.count() == 0:
    call_command('loaddata', 'dados_blog.json')
    print('✅ Dados iniciais carregados')
else:
    print('⚠️ Dados já existem, pulando carga')
"
fi

# 4. Migrações (já está no seu script)
echo "Executando migrações..."
if python3 manage.py migrate --no-input; then
    echo "Migrações: OK"
else
    echo "ERRO NAS MIGRAÇÕES"
fi

# 5. Coleta de estáticos
echo "Coletando arquivos estáticos..."
python3 manage.py collectstatic --no-input

# 6. Inicialização do Gunicorn
PORT=$(echo "$PORT" | sed 's/^0*//')
PORT=${PORT:-8000}
echo "Lançando Gunicorn na porta $PORT..."
exec gunicorn sitio.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 3 \
    --timeout 120 \
    --log-level debug \
    --access-logfile - \
    --error-logfile -