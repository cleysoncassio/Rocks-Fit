#!/bin/bash
# build.sh — Executado durante o build na Hostman (PRODUÇÃO)

# Para o script imediatamente em caso de erro
set -e

# Garante que o Django use as configurações de produção
export DJANGO_SETTINGS_MODULE=sitio.settings.production

echo "=== INICIANDO BUILD DE PRODUÇÃO ==="

# (OPCIONAL) RESET DE SEGURANÇA: Coloca todos os alunos como INATIVO para iniciar o novo fluxo.
# Descomente a linha abaixo apenas no próximo deploy para limpar o status de produção uma única vez.
# python3 manage.py shell -c "from blog.models import Aluno; Aluno.objects.all().update(status='INATIVO')"

# Instala dependências
echo "Instalando dependências..."
pip install --upgrade pip
pip install -r requirements.txt

# ============================================
# CONCEDER PERMISSÕES DO BANCO (CRÍTICO!)
# ============================================
echo "Configurando permissões do banco de dados..."
python3 -c "
from django.db import connection
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sitio.settings.production')
django.setup()
try:
    with connection.cursor() as cursor:
        cursor.execute('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO CURRENT_USER;')
        cursor.execute('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO CURRENT_USER;')
        cursor.execute('GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO CURRENT_USER;')
        cursor.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO CURRENT_USER;')
        cursor.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO CURRENT_USER;')
        print('✅ Permissões do banco configuradas com sucesso')
except Exception as e:
        print(f'⚠️ Aviso ao configurar permissões: {e}')
"

# Executa migrações
echo "Executando migrações..."
python3 manage.py makemigrations --noinput || true
python3 manage.py migrate --noinput

# Carrega dados iniciais (REMOVIDO EM PRODUÇÃO PARA NÃO SOBRESCREVER DADOS REAIS)
# if [ -f "dados_blog.json" ]; then
#     echo "Carregando dados iniciais..."
#     python3 manage.py loaddata dados_blog.json || true
# fi

# Coleta arquivos estáticos
echo "Coletando arquivos estáticos..."
python3 manage.py collectstatic --noinput

echo "=== BUILD CONCLUÍDO COM SUCESSO ==="