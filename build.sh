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
# Usa o management command robusto que verifica e reporta o resultado
# ============================================
echo "Passo 2b: Configurando permissões do banco de dados..."
python3 manage.py fix_db_permissions || echo "AVISO: fix_db_permissions retornou erro (ver log acima)."

# Coleta arquivos estáticos
echo "Passo 3: Coletando arquivos estáticos..."
python3 manage.py collectstatic --noinput

echo "=== BUILD CONCLUÍDO COM SUCESSO ==="