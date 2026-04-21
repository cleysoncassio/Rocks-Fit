#!/bin/sh
# start.sh — Inicia o servidor Gunicorn na Hostman

# Garante que o Django use as configurações de produção
export DJANGO_SETTINGS_MODULE=sitio.settings.production

echo "=== ROCKS-FIT: INICIANDO AMBIENTE ==="

# 1. Pulso de Sincronização (Regra da Hostman: Evento único antes do servidor)
# Gera o dados_blog.json necessário para a catraca uma única vez no boot de forma direta.
echo "[BOOT] Sincronizando cache de alunos..."
python3 manage.py shell -c "from blog.models import exportar_alunos_json; exportar_alunos_json(None, None)"

# 2. Configura a porta
PORT="${PORT:-8080}"

echo "=== ROCKS-FIT: SUBINDO SERVIDOR WEB (GUNICORN) ==="
# Launch server process immediately after the single pulse
exec gunicorn sitio.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -