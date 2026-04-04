@echo off
setlocal
:: FIX DO CAMINHO: Garante que o script rode na pasta onde o .bat esta salvo
cd /d "%~dp0"
title Ponte Rocks Fit - Produção

echo ==========================================
echo    SISTEMA DE ACESSO ROCKS FIT
echo ==========================================
echo.

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
echo Verificando bibliotecas basicas (Interface)...
%PY_CMD% -m pip install requests pillow customtkinter opencv-python --quiet

echo Verificando bibliotecas de IA (Opcional)...
:: Nao usamos --quiet aqui para o usuario ver se ha erro, mas nao interrompemos o script
%PY_CMD% -m pip install face-recognition cmake dlib

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
