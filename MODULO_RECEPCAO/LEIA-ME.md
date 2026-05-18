# 🚀 Módulo de Recepção Rocks-Fit (Windows)

Este módulo é responsável pelo monitoramento de biometria facial e controle de acesso da academia Rocks-Fit. Ele se comunica com o CRM online para validar alunos e registrar acessos.

## 📋 Pré-requisitos

Antes de começar, você precisará ter instalado em seu Windows:

1. **Python 3.10 ou superior**: [Download Python](https://www.python.org/downloads/windows/)
   - *IMPORTANTE: Marque a opção "Add Python to PATH" durante a instalação.*
2. **Câmera USB (Webcam)** conectada e funcional.
3. **Dependências do Face Recognition** (Opcional, mas recomendado para biometria neural):
   - Instale o [CMake](https://cmake.org/download/).
   - Instale as "Ferramentas de Compilação do C++" no Visual Studio.
4. **Git para Windows** (Recomendado para evitar erros de biblioteca): [Download Git](https://git-scm.com/download/win)

---

## 🛠️ Passo a Passo de Instalação

### 1. Criar Ambiente Virtual (Recomendado)
Abra o Prompt de Comando (CMD) ou PowerShell na pasta `MODULO_RECEPCAO` e execute:

```bash
# Cria o ambiente virtual
python -m venv .venv

# Ativa o ambiente virtual
.venv\Scripts\activate
```

### 2. Instalar Bibliotecas
Com o ambiente virtual ativado, instale as dependências necessárias:

```bash
pip install -r requirements.txt
```

*Nota: Se a instalação do `face-recognition` falhar, o sistema ainda funcionará usando o motor reserva (ORB), mas a precisão será menor.*

---

## 🏃 Como Rodar o Sistema

### Via Linha de Comando
Com o ambiente virtual ativado:
```bash
python ponte_rocksfit_flet.py
```

### Via Atalho (Batch File)
Você pode simplesmente dar um clique duplo no arquivo:
- `INICIAR_ROCKSFIT.bat`

O sistema abrirá uma janela do navegador (Dashboard) e você poderá gerenciar a entrada dos alunos.

---

## 💡 Comandos Úteis (Virtualenv)

- **Criar:** `python -m venv .venv`
- **Ativar:** `.venv\Scripts\activate`
- **Desativar:** `deactivate`
- **Verificar pacotes:** `pip list`

---

## 🔧 Solução de Problemas

- **Câmera não detectada:** Verifique se nenhuma outra aplicação (como Zoom ou Meet) está usando a câmera.
- **Erro de Conexão CRM:** Verifique se o computador tem acesso à internet e se o token no arquivo `.py` está correto.
- **Biometria não funciona no CRM:** Certifique-se de que o `ponte_rocksfit_flet.py` está rodando. O CRM web se comunica com ele através da porta `8553`.
- **Tela Preta:** O sistema usa o Flet. Se a interface não carregar, tente abrir no navegador através do endereço `http://127.0.0.1:8552`.
- **Erro "Please install face_recognition_models":** Ocorre no Windows sem Git. Com o ambiente virtual ativado, execute:
  ```bash
  pip install face-recognition-models
  ```
  *Se o erro persistir, force a reinstalação:*
  ```bash
  pip install --force-reinstall face-recognition-models
  ```

---
*Desenvolvido para Rocks-Fit – Gestão Inteligente de Academias.*
