# 🚀 Guia de Instalação - Rocks Fit Academia

Este guia explica como configurar o Módulo de Recepção no computador Windows da academia.

## 1. Preparação
1. Certifique-se de que o Python 3.10 ou superior está instalado.
2. Verifique se o cabo da catraca está conectado à placa de rede e o IP configurado como estático:
   - **IP do Computador:** `169.254.37.1`
   - **Máscara:** `255.255.255.0`
   - **IP da Catraca:** `169.254.37.150` (Porta 1001)

## 2. Instalação
Abra o terminal (CMD) dentro da pasta `MODULO_RECEPCAO` e execute:

```cmd
# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente
.venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt
```

## 3. Primeiro Teste (Com Visibilidade)
Antes de usar o lançador automático, rode manualmente para ver se há erros:
```cmd
python ponte_rocksfit_flet.py
```
*Observe se aparece: `✅ Sync Finalizado` e se a catraca responde aos comandos.*

## 4. Uso Diário
Após validar que tudo funciona, basta clicar duas vezes no arquivo:
👉 **`INICIAR_ROCKSFIT.bat`**

O sistema iniciará em segundo plano e abrirá a interface no navegador ou em janela dedicada.

---
**Suporte:** rocksfit@2024 | Token de Sincronização Ativo.
