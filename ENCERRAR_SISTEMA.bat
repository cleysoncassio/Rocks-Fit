@echo off
title Encerrar Sistema Rocks Fit
echo [INFO] Encerrando processos da Ponte Rocks Fit...
taskkill /F /IM python.exe /T
echo [OK] Sistema encerrado com sucesso.
pause
