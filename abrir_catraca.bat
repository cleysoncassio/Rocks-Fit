@echo off
setlocal
:: FIX DO CAMINHO: Garante que o script rode na pasta onde o .bat esta salvo
cd /d "%~dp0"
title Ponte Rocks Fit - Produção

echo ==========================================
echo    SISTEMA DE ACESSO ROCKS FIT
echo ==========================================
echo.

:: Limpa processos fantasmas para evitar erro de porta
taskkill /F /IM python.exe /T >nul 2>&1
echo [INFO] Inicializando ambiente limpo...

:: Tenta encontrar o Python
set PY_CMD=
where py >nul 2>&1
if %errorlevel% equ 0 (set PY_CMD=py)
where python >nul 2>&1
if %errorlevel% equ 0 (set PY_CMD=python)

if not defined PY_CMD (
    echo [ERRO] Python nao encontrado! Marque "Add Python to PATH" na instalacao.
    pause
    exit
)

echo [OK] Python detectado: %PY_CMD%
echo Verificando integridade das bibliotecas...

:: Verifica se a biblioteca base ja existe para evitar o delay do pip install em todos os acessos
%PY_CMD% -c "import requests, PIL, customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Instalando dependencias pela primeira vez (isso pode levar 1 minuto)...
    %PY_CMD% -m pip install requests pillow customtkinter opencv-python --quiet
) else (
    echo [OK] Bibliotecas verificadas.
)

:: Tentativa silenciosa de upgrade apenas de bibliotecas criticas se necessario
:: %PY_CMD% -m pip install --upgrade requests --quiet

echo.
echo [INFO] Abrindo monitor da recepcao...
echo [DICA] Use ESC para fechar ou F2/F3 para abrir manualmente.
echo.

%PY_CMD% ponte_rocksfit.py

if %errorlevel% neq 0 (
    echo.
    echo [AVISO] O script fechou com erro. Verifique se o Python esta no PATH.
    pause
)
