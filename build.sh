#!/bin/bash
# build.sh — Executado durante o build na Hostman (PRODUÇÃO)

# Para o script imediatamente em caso de erro
set -e

# Garante que o Django use as configurações de produção
export DJANGO_SETTINGS_MODULE=sitio.settings.production

echo "=== INICIANDO BUILD DE PRODUÇÃO ==="

# 1. Instala dependências (OBRIGATÓRIO SER PRIMEIRO)
echo "Instalando dependências..."
pip install --upgrade pip
pip install -r requirements.txt

# 2. Configurações de Banco de Dados
echo "Executando tarefas de banco de dados..."

# Executa migrações (DEVE SER ANTES DE CONCEDER PERMISSÕES)
echo "Passo 2a: Executando migrações..."
python3 manage.py migrate --noinput

# ============================================
# CONCEDER PERMISSÕES DO BANCO (CRÍTICO!)
# ============================================
echo "Passo 2b: Configurando permissões do banco de dados..."
python3 -c "
import os, sys, django
from django.db import connection
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sitio.settings.production')
print('[PYTHON] Inicializando ambiente Django...')
sys.stdout.flush()
try:
    django.setup()
    print('[PYTHON] Ambiente carregado. Concedendo privilégios...')
    sys.stdout.flush()
    with connection.cursor() as cursor:
        cursor.execute('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO CURRENT_USER;')
        cursor.execute('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO CURRENT_USER;')
        cursor.execute('GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO CURRENT_USER;')
        cursor.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO CURRENT_USER;')
        cursor.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO CURRENT_USER;')
        print('✅ Permissões do banco configuradas com sucesso')
except Exception as e:
    print(f'⚠️ Aviso ao configurar permissões: {e}')
    import traceback
    traceback.print_exc()
sys.stdout.flush()
"

# Coleta arquivos estáticos
echo "Passo 3: Coletando arquivos estáticos..."
python3 manage.py collectstatic --noinput

echo "=== BUILD CONCLUÍDO COM SUCESSO ==="