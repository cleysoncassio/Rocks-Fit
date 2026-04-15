import os
import sys
import requests

# Configurações
API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = "qwen/qwen-plus"

def perguntar_ao_agente(pergunta, contexto_arquivo=None):
    url = "https://openrouter.ai/api/v1/chat/completions"
    conteudo_arquivo = ""
    
    if contexto_arquivo and os.path.exists(contexto_arquivo):
        with open(contexto_arquivo, "r") as f:
            conteudo_arquivo = f.read()

    prompt_sistema = "Você é a Bia, assistente especialista em Django e Data Science para os projetos Rocks-Fit e AdvLegal."
    prompt_usuario = f"Contexto do arquivo ({contexto_arquivo}):\n\n{conteudo_arquivo}\n\nPergunta: {pergunta}"

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ]
    }

    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        print("\n--- RESPOSTA DA BIA ---")
        print(response.json()['choices'][0]['message']['content'])
    else:
        print(f"Erro: {response.status_code} - {response.text}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: agente 'sua pergunta' [caminho_do_arquivo]")
    else:
        user_query = sys.argv[1]
        file_path = sys.argv[2] if len(sys.argv) > 2 else None
        perguntar_ao_agente(user_query, file_path)