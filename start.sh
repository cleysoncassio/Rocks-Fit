#!/bin/sh
# Script de inicialização Ultrarrobusto para Hostman
# Compatível com /bin/sh e gerenciamento de sinais (exec)

echo "--- INICIANDO APLICAÇÃO ---"

# 1. Diagnóstico básico
echo "Python: $(python3 -V)"
echo "Diretório atual: $(pwd)"

# 2. Migrações com proteção contra crash imediato
echo "Executando migrações..."
if python3 manage.py migrate --no-input; then
    echo "Migrações: OK"
else
    echo "ERRO NAS MIGRAÇÕES: Verifique se o DATABASE_URL está correto (não use localhost)."
    # Mantemos o script rodando para que os logs fiquem visíveis no painel
fi

# 3. Coleta de estáticos (Garante que o WhiteNoise funcione)
echo "Coletando arquivos estáticos..."
python3 manage.py collectstatic --no-input

# 4. Inicialização do Gunicorn com 'exec'
# Garantimos que a porta não tenha zeros à esquerda para evitar erros
PORT=$(echo "$PORT" | sed 's/^0*//')
PORT=${PORT:-8000}
echo "Lançando Gunicorn na porta $PORT..."
exec gunicorn sitio.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 3 \
    --timeout 120 \
    --log-level debug \
    --access-logfile - \
    --error-logfile -
