#!/bin/bash
# build.sh — Executado durante o BUILD na Hostman (construção da imagem Docker)
#
# ⚠️  IMPORTANTE: O banco de dados NÃO está disponível durante o build.
# Por isso, migrate e fix_db_permissions ficam APENAS no start.sh (runtime).
#
# Este script faz apenas:
#  1. Instala dependências Python
#  2. Coleta arquivos estáticos (não requer banco)

set -e

export DJANGO_SETTINGS_MODULE=sitio.settings.production

echo "=== INICIANDO BUILD DE PRODUÇÃO ==="

# 1. Instala dependências
echo "Passo 1: Instalando dependências..."
pip install --upgrade pip
pip install -r requirements.txt

# 2. Coleta arquivos estáticos (não acessa banco)
echo "Passo 2: Coletando arquivos estáticos..."
python3 manage.py collectstatic --noinput

echo "=== BUILD CONCLUÍDO COM SUCESSO ==="
echo "Nota: migrate e fix_db_permissions serão executados no startup (start.sh)."