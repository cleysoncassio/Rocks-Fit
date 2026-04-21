#!/bin/sh
# start.sh — Inicia o servidor Gunicorn na Hostman

# Garante que o Django use as configurações de produção
export DJANGO_SETTINGS_MODULE=sitio.settings.production

echo "=== ROCKS-FIT: INICIANDO SERVIDOR WEB ==="

# Coleta a porta da variável de ambiente ou usa 8080 como fallback
PORT="${PORT:-8080}"

# Inicia o Gunicorn
# Nota: Migrações e sincronizações pesadas agora são feitas no build.sh
exec gunicorn sitio.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -