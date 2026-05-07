# 🐧 Guia de Instalação - Rocks-Fit (Linux/Debian)

Este guia contém as instruções para configurar o módulo de recepção em uma máquina Linux (Debian, Ubuntu, etc).

## 1. Dependências do Sistema
O hardware de biometria e o reconhecimento facial exigem pacotes do sistema:

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv libfprint-2-2 fprintd libpam-fprintd cmake build-essential libopenblas-dev liblapack-dev libx11-dev libgtk-3-dev
```

## 2. Permissões de Biometria
Para que o software possa acessar o leitor de digital sem pedir senha:

```bash
# Rode o script de liberação que acompanha este módulo
chmod +x liberar_biometria.sh
sudo ./liberar_biometria.sh
```

## 3. Ambiente Python
Crie e configure o ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements_recepcao.txt
```

## 4. Configuração
1. Copie o arquivo `.env.example` para `.env`.
2. Edite o `.env` com a URL do seu CRM e o Token.

## 5. Execução
Com o ambiente ativado:
```bash
python ponte_rocksfit_flet.py
```

---
**Dica:** Se a interface carregar com tela preta, verifique se o driver de vídeo está atualizado ou abra no navegador em `http://localhost:8552`.
