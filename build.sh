#!/bin/bash
# build.sh — Executado durante o build na Hostman (PRODUÇÃO)

# Para o script imediatamente em caso de erro
set -e

# Garante que o Django use as configurações de produção
export DJANGO_SETTINGS_MODULE=sitio.settings.production

echo "Iniciando build de Producão..."

# Instala dependências
pip install --upgrade pip
pip install -r requirements.txt

# Coleta arquivos estáticos
python3 manage.py collectstatic --noinput

# Aplica migrações - O BUILD VAI PARAR AQUI SE FALHAR
echo "Aplicando migrações no banco de dados..."
python3 manage.py migrate --noinput

# Carrega dados iniciais se o banco estiver vazio
if [ -f "dados_blog.json" ]; then
    python3 -c "
import django; django.setup()
from blog.models import Program
if Program.objects.count() == 0:
    from django.core.management import call_command
    call_command('loaddata', 'dados_blog.json')
    print('Dados iniciais carregados.')
else:
    print('Dados ja existem - pulando loaddata.')
"
fi

echo "Build concluído com sucesso."

# 🚨 RESET DE SENHA TEMPORÁRIO (PARA PRODUÇÃO)
echo "Iniciando script de emergência para reset de senha..."
python3 -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sitio.settings.production')
django.setup()
from blog.models import User
# Reset ccs
u = User.objects.filter(username='ccs').first()
if u:
    u.set_password('admin123')
    u.is_staff = True
    u.is_active = True
    u.is_superuser = True
    u.save()
    print('✅ Senha de ccs resetada no PostgreSQL.')
else:
    print('⚠️ Usuario ccs nao encontrado em producao.')

# Cria suporte_rocks se não existir
if not User.objects.filter(username='suporte_rocks').exists():
    try:
        User.objects.create_superuser('suporte_rocks', 'suporte@rocksfit.com.br', 'rocks2026')
        print('✅ Usuario suporte_rocks criado no PostgreSQL.')
    except Exception as e:
        print(f'❌ Erro ao criar suporte_rocks: {e}')
else:
    u_s = User.objects.get(username='suporte_rocks')
    u_s.set_password('rocks2026')
    u_s.save()
    print('✅ Senha de suporte_rocks atualizada no PostgreSQL.')
"