@echo off
setlocal
cd /d "%~dp0"
title Rocks Fit - Inicialização Completa

echo ==========================================
echo    ROCKS FIT - CARREGANDO SISTEMA
echo ==========================================
echo.

:: Detecta comando Python
set PY_CMD=python
where py >nul 2>&1 && set PY_CMD=py

echo [1/3] Iniciando Monitor e Gestor...
start "" %PY_CMD% ponte_rocksfit.py

echo [2/3] Iniciando Interface Biometrica...
start "" %PY_CMD% leitor_bio.py

echo [3/3] Verificando conexao...
timeout /t 2 >nul

echo.
echo ✅ SISTEMA EM OPERACAO.
echo Nao feche as janelas pretas que abriram.
echo.
pause
