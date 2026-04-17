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
echo "Limpando bloqueios de segurança (Axes)..."
python3 manage.py axes_reset || echo "Axes nao instalado ou erro ao limpar."

echo "Iniciando script de emergência de Autenticação..."
python3 -c "
import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sitio.settings.production')
try:
    django.setup()
    User = get_user_model()
    
    # 1. Resetar CCS
    u = User.objects.filter(username='ccs').first()
    if u:
        u.set_password('admin123')
        u.is_staff = True
        u.is_active = True
        u.is_superuser = True
        u.save()
        print('✅ [SYNC] Senha de ccs redefinida no Banco de Produção.')
    else:
        print('⚠️ [SYNC] Usuário ccs não encontrado.')

    # 2. Garantir Suporte Rocks
    u_s, created = User.objects.get_or_create(username='suporte_rocks', defaults={'email': 'suporte@rocksfit.com.br'})
    u_s.set_password('rocks2026')
    u_s.is_staff = True
    u_s.is_active = True
    u_s.is_superuser = True
    u_s.save()
    if created: print('✅ [SYNC] Novo superusuário suporte_rocks criado.')
    else: print('✅ [SYNC] Senha do suporte_rocks atualizada.')

except Exception as e:
    print(f'❌ [ERRO CRÍTICO NO RESET]: {e}')
"