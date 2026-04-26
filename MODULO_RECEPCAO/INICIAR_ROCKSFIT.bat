@echo off
:: Lançador Universal Rocks-Fit (Windows)
cd /d "%~dp0"

:: 1. Tenta encontrar o Python na pasta atual (Caso do seu print)
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "ponte_rocksfit.py"
    exit
)

:: 2. Tenta encontrar o Python na pasta de cima (Caso padrão)
cd ..
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "MODULO_RECEPCAO\ponte_rocksfit.py"
    exit
)

echo [ERRO] Nao foi possivel encontrar a pasta .venv. 
echo Certifique-se de que o ambiente virtual foi instalado corretamente.
pause
