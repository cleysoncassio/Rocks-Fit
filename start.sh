#!/bin/bash
# Script de inicialização para o Django no Hostman
# Este script garante que as migrações ocorram antes de subir o servidor

echo "Rodando migrações..."
python manage.py migrate --no-input

echo "Subindo o servidor Gunicorn..."
# O Hostman usa 0.0.0.0 e a variável $PORT para o mapeamento interno
gunicorn sitio.wsgi:application -b :$PORT --log-file -
