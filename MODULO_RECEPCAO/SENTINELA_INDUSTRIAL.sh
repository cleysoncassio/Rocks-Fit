#!/bin/bash
# =================================================================
# ROCKS-FIT: SENTINELA INDUSTRIAL 24/7 (LINUX)
# Este script garante que o sistema de biometria nunca fique fora do ar.
# =================================================================

# Cores para o terminal
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🛡️ [SENTINELA] Vigilante Industrial Rocks-Fit Ativo.${NC}"

# Loop Infinito de Vigilância
while true; do
    echo -e "${YELLOW}🚀 [SENTINELA] Iniciando Módulo de Recepção...${NC}"
    
    # Executa a ponte principal utilizando o ambiente virtual se disponível
    if [ -f "../.venv/bin/python" ]; then
        echo -e "${GREEN}📦 [SISTEMA] Usando Python do Ambiente Virtual (.venv)${NC}"
        ../.venv/bin/python ponte_rocksfit_flet.py
    elif [ -f ".venv/bin/python" ]; then
        echo -e "${GREEN}📦 [SISTEMA] Usando Python do Ambiente Virtual Local (.venv)${NC}"
        .venv/bin/python ponte_rocksfit_flet.py
    else
        echo -e "${YELLOW}⚠️ [SISTEMA] Ambiente Virtual (.venv) não encontrado. Usando Python3 global...${NC}"
        python3 ponte_rocksfit_flet.py
    fi
    
    # Se o processo acima sair (crash ou fechamento), registra e reinicia
    EXIT_CODE=$?
    echo -e "${RED}⚠️ [SENTINELA] O sistema parou inesperadamente (Código: $EXIT_CODE).${NC}"
    
    # Limpeza nuclear antes de reiniciar para garantir que o hardware USB seja liberado
    echo -e "${YELLOW}🧹 [SENTINELA] Realizando limpeza nuclear de hardware...${NC}"
    pkill -9 fprintd
    pkill -9 fprintd-verify
    pkill -9 monitor_aluno.py
    pkill -9 flet
    
    echo -e "${GREEN}🔄 [SENTINELA] Reiniciando em 5 segundos...${NC}"
    sleep 5
done
