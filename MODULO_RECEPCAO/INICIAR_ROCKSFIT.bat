@echo off
:: Script de Inicialização Silenciosa para Windows
cd /d "%~dp0.."
start "" ".venv\Scripts\pythonw.exe" "MODULO_RECEPCAO\ponte_rocksfit.py"
exit
