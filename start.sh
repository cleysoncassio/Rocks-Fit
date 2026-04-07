#!/bin/bash
# Script de inicialização Robusto para o Django no Hostman
# Este script inclui diagnósticos para identificar falhas no deploy

echo "--- DIAGNÓSTICO DE INICIALIZAÇÃO ---"
echo "Data/Hora: $(date)"
echo "Python versão: $(python3 --version)"
echo "Verificando arquivos..."
ls -l manage.py
ls -d sitio

echo "--- RODANDO MIGRAÇÕES ---"
# O uso de python3 garante compatibilidade com a imagem base do Hostman
if python3 manage.py migrate --no-input; then
    echo "Sucesso: Migrações concluídas."
else
    echo "ERRO CRÍTICO: Falha ao rodar as migrações."
    echo "Verifique se a variável DATABASE_URL está correta e o banco está online."
    # Não vamos interromper o script aqui para evitar o crash loop imediato
    # e permitir que os logs de erro apareçam no console.
fi

echo "--- SUBINDO O SERVIDOR GUNICORN ---"
# Usamos 0.0.0.0 e logs de debug para visibilidade total
gunicorn sitio.wsgi:application \
    -b 0.0.0.0:$PORT \
    --log-level debug \
    --access-logfile - \
    --error-logfile -
