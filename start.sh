#!/bin/sh
# start.sh — Inicia o servidor Gunicorn na Hostman

# Garante que o Django use as configurações de produção
export DJANGO_SETTINGS_MODULE=sitio.settings.production

echo "=== ROCKS-FIT: INICIANDO AMBIENTE ==="

# 1. Tarefas Pré-Start (Executadas em BACKGROUND para não travar o Gunicorn)
echo "[BOOT] Iniciando auto-reparo, migrações e sincronização em segundo plano..."
(
    echo "[BOOT] Executando auto-reparo de permissões do banco..."
    python3 manage.py shell -c "from django.db import connection; 
with connection.cursor() as cursor:
    try:
        cursor.execute('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO Rocksfit;')
        cursor.execute('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO Rocksfit;')
        print('✅ Permissões concedidas com sucesso!')
    except Exception as e:
        print(f'❌ Falha no auto-reparo: {e}')" || echo "Aviso: Script de reparo falhou."

    python3 manage.py migrate --noinput || echo "AVISO: Falha na migração no boot."
    if [ -f "master_production_data.json" ]; then
        SKIP_SIGNALS=1 python3 manage.py loaddata master_production_data.json || echo "AVISO: Falha no loaddata."
    fi
    python3 manage.py shell -c "from blog.models import exportar_alunos_json; exportar_alunos_json(None, None)"
) &

# 2. Configura a porta
PORT="${PORT:-8080}"

echo "=== ROCKS-FIT: SUBINDO SERVIDOR WEB IMEDIATAMENTE (GUNICORN) ==="
# O servidor sobe agora. A Hostman verá o site como ONLINE em segundos.
exec gunicorn sitio.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -