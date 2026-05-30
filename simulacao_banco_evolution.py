import requests
import json
import time

# Configurações locais da Evolution API (Mesmas do test_send_message.py)
BASE_URL = "http://localhost:8080"
GLOBAL_API_KEY = "429683C4C977415CBEE243405C76100E"
INSTANCE_NAME = "Rocksfit-business"

HEADERS = {
    "apikey": GLOBAL_API_KEY,
    "Content-Type": "application/json"
}

# --- SIMULAÇÃO DO BANCO DE DADOS ---
# Vamos simular uma consulta que retorna clientes com pendências, aniversariantes ou novas matrículas
def consultar_banco_de_dados():
    print("🔍 [SIMULAÇÃO] Consultando banco de dados por alunos...")
    # Simulando um tempo de processamento/query
    time.sleep(1)
    
    # Mock de dados retornados pela query
    alunos_simulados = [
        {
            "id": 1,
            "nome": "João da Silva",
            "telefone": "5584999999999",  # Substituir por um número de teste real
            "status_pagamento": "vencido",
            "dias_vencimento": 3
        },
        {
            "id": 2,
            "nome": "Maria Oliveira",
            "telefone": "5584988888888",  # Substituir por um número de teste real
            "status_pagamento": "proximo_vencimento",
            "dias_vencimento": -2
        }
    ]
    
    print(f"✅ [SIMULAÇÃO] Consulta retornou {len(alunos_simulados)} alunos.")
    return alunos_simulados

# --- FUNÇÃO PARA ENVIAR MENSAGEM VIA EVOLUTION API ---
def enviar_mensagem_evolution(aluno):
    print(f"\n📨 Preparando envio para: {aluno['nome']} ({aluno['telefone']})")
    
    # Personalização da mensagem com base no status do banco
    if aluno['status_pagamento'] == 'vencido':
        texto_mensagem = (
            f"Olá {aluno['nome']}, tudo bem?\n"
            f"Verificamos em nosso sistema que sua mensalidade na Rocks-Fit venceu há {aluno['dias_vencimento']} dias.\n"
            "Qualquer dúvida, estamos à disposição para ajudar!"
        )
    elif aluno['status_pagamento'] == 'proximo_vencimento':
        dias_abs = abs(aluno['dias_vencimento'])
        texto_mensagem = (
            f"Oi {aluno['nome']}! Passando pra lembrar que sua mensalidade Rocks-Fit "
            f"vence em {dias_abs} dias.\nNão perca o foco nos treinos! 💪"
        )
    else:
        texto_mensagem = f"Olá {aluno['nome']}! Temos novidades na Rocks-Fit."

    # Endpoint para enviar texto na Evolution API
    url = f"{BASE_URL}/message/sendText/{INSTANCE_NAME}"
    payload = {
        "number": aluno["telefone"],
        "text": texto_mensagem
    }
    
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, ensure_ascii=False)}")
    
    # Envio da requisição
    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=10)
        if response.status_code in [200, 201]:
            print(f"✅ Sucesso ao enviar para {aluno['nome']}!")
            # print(response.json()) # Descomente para ver o retorno completo da API
        else:
            print(f"❌ Falha ao enviar para {aluno['nome']}. HTTP {response.status_code}")
            print(f"Erro: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"🚨 Erro de conexão com a Evolution API local: {e}")
        print("Certifique-se de que o Docker da Evolution API está rodando na porta 8080.")

# --- FLUXO PRINCIPAL ---
def iniciar_teste():
    print("="*50)
    print("🚀 INICIANDO TESTE DO AMBIENTE EVOLUTION API LOCAL")
    print("="*50)
    
    numero_teste = input("📱 Digite o seu número de WhatsApp para os testes (Ex: 5584999999999): ")
    if not numero_teste.strip():
        print("Número não fornecido. Teste cancelado.")
        return

    alunos = consultar_banco_de_dados()
    
    # Substituir os números simulados pelo número de teste inserido
    for aluno in alunos:
        aluno['telefone'] = numero_teste.strip()
        
    for aluno in alunos:
        enviar_mensagem_evolution(aluno)
        # Pausa para não sobrecarregar a API
        time.sleep(2)
        
    print("\n🏁 Teste finalizado.")

if __name__ == "__main__":
    iniciar_teste()
