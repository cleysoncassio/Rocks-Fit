#!/bin/sh
# Script de inicialização UNIFICADO para Hostman
# Executa todas as tarefas necessárias: permissões, migrações, dados, estáticos e Gunicorn

echo "========================================="
echo "   INICIANDO APLICAÇÃO - ROCKS FIT"
echo "========================================="

# 1. Diagnóstico básico
echo "📌 Python: $(python3 -V)"
echo "📌 Diretório atual: $(pwd)"
echo "📌 Porta: ${PORT:-8000}"

# 2. Configurar permissões do banco (ignora erros se já tiver)
echo ""
echo "🔧 Configurando permissões do banco de dados..."
python3 -c "
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO CURRENT_USER;')
        cursor.execute('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO CURRENT_USER;')
        cursor.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO CURRENT_USER;')
        cursor.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO CURRENT_USER;')
        print('✅ Permissões do banco configuradas com sucesso')
except Exception as e:
        print(f'⚠️ Aviso ao configurar permissões (pode ser normal): {e}')
"

# 3. Carregar dados iniciais (somente se o arquivo existir e as tabelas estiverem vazias)
echo ""
echo "📦 Verificando dados iniciais..."
if [ -f "dados_blog.json" ]; then
    python3 -c "
from django.core.management import call_command
from django.apps import apps
try:
    # Verifica se alguma tabela do app blog já tem dados
    from blog.models import Program, Trainer, Plan
    total = Program.objects.count() + Trainer.objects.count() + Plan.objects.count()
    if total == 0:
        call_command('loaddata', 'dados_blog.json')
        print('✅ Dados iniciais carregados com sucesso')
    else:
        print('⚠️ Dados já existem no banco - pulando carga inicial')
except Exception as e:
        print(f'⚠️ Erro ao carregar dados: {e}')
"
else
    echo "⚠️ Arquivo dados_blog.json não encontrado - pulando carga de dados"
fi

# 4. Executar migrações
echo ""
echo "🔄 Executando migrações..."
if python3 manage.py migrate --no-input; then
    echo "✅ Migrações aplicadas com sucesso"
else
    echo "❌ ERRO NAS MIGRAÇÕES - Verifique a conexão com o banco de dados"
    # Mantém o script rodando para que os logs fiquem visíveis
fi

# 5. Coletar arquivos estáticos
echo ""
echo "📁 Coletando arquivos estáticos..."
if python3 manage.py collectstatic --no-input; then
    echo "✅ Arquivos estáticos coletados com sucesso"
else
    echo "⚠️ Aviso: Problemas na coleta de arquivos estáticos"
fi

# 6. Criar superusuário se não existir (opcional - descomente se quiser)
# echo ""
# echo "👤 Verificando superusuário..."
# python3 -c "
# from django.contrib.auth.models import User
# if not User.objects.filter(is_superuser=True).exists():
#     User.objects.create_superuser('admin', 'admin@exemplo.com', 'admin123')
#     print('✅ Superusuário criado (admin/admin123)')
# else:
#     print('✅ Superusuário já existe')
# "

# 7. Inicializar Gunicorn
echo ""
echo "========================================="
echo "   🚀 INICIANDO SERVIDOR GUNICORN 🚀"
echo "========================================="

# Garantir que a porta não tenha zeros à esquerda
PORT=$(echo "$PORT" | sed 's/^0*//')
PORT=${PORT:-8000}

echo "📌 Servidor rodando em: http://0.0.0.0:$PORT"
echo "📌 Workers: 3"
echo "📌 Timeout: 120s"
echo ""

# Executa o Gunicorn (o 'exec' substitui o processo atual)
exec gunicorn sitio.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 3 \
    --timeout 120 \
    --log-level debug \
    --access-logfile - \
    --error-logfile -