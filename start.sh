#!/bin/sh
# start.sh — Inicia o servidor Gunicorn na Hostman
# CORREÇÃO CRÍTICA: O fix_db_permissions agora roda ANTES do Gunicorn,
# eliminando o race condition que causava "permission denied for table blog_trainer".

export DJANGO_SETTINGS_MODULE=sitio.settings.production

echo "=== ROCKS-FIT: INICIANDO AMBIENTE ==="

# 1. Migrações (em primeiro plano — banco DEVE estar pronto antes de tudo)
echo "[BOOT] Executando migrações..."
python3 manage.py migrate --noinput || echo "AVISO: Falha na migração no boot."

# 2. CORRIGIR PERMISSÕES — DEVE RODAR ANTES DO GUNICORN (em primeiro plano)
# Sem isso, as primeiras requisições falham com "permission denied for table blog_trainer"
echo "[BOOT] Corrigindo permissões do banco de dados (CRÍTICO)..."
python3 manage.py fix_db_permissions || echo "AVISO: fix_db_permissions falhou (verificar logs acima)."

# 3. Tarefas secundárias em background (não bloqueiam o servidor)
echo "[BOOT] Iniciando tarefas de sincronização em segundo plano..."
(
    if [ -f "master_production_data.json" ]; then
        SKIP_SIGNALS=1 python3 manage.py loaddata master_production_data.json || echo "AVISO: Falha no loaddata."
    fi
) &

# 4. Configura a porta
PORT="${PORT:-8080}"

echo "=== ROCKS-FIT: SUBINDO SERVIDOR WEB (GUNICORN) ==="
exec gunicorn sitio.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -