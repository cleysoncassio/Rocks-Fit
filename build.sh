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

echo "Build de ativos e dependências concluído com sucesso."# Force rebuild
