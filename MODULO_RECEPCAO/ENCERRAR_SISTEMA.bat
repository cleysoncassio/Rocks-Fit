@echo off
title Encerrar Sistema Rocks Fit
echo [INFO] Encerrando processos da Recepcao...
taskkill /F /IM pythonw.exe /T >nul 2>&1
taskkill /F /IM python.exe /T >nul 2>&1
echo [OK] Sistema encerrado.
timeout /t 2 >nul
exit
