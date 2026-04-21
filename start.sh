#!/bin/sh
# start.sh — Inicia o servidor Gunicorn na Hostman

# Garante que o Django use as configurações de produção
export DJANGO_SETTINGS_MODULE=sitio.settings.production

echo "=== ROCKS-FIT: INICIANDO AMBIENTE ==="

# 1. Pulso de Sincronização (Regra da Hostman: Evento único antes do servidor)
# Isso gera o dados_blog.json necessário para a catraca uma única vez no boot.
echo "[BOOT] Pulso de sincronização de cache de alunos..."
python3 manage.py shell -c "from blog.models import Aluno; a=Aluno.objects.first(); a.save() if a else print('Base de alunos vazia.')"

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