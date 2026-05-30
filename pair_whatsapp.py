import requests

BASE_URL = "http://localhost:8080"
GLOBAL_API_KEY = "429683C4C977415CBEE243405C76100E"
INSTANCE_NAME = "Rocksfit-business"

HEADERS = {
    "apikey": GLOBAL_API_KEY,
    "Content-Type": "application/json"
}

def delete_instance():
    # Remove a instância se já existir para forçar a criação limpa
    url = f"{BASE_URL}/instance/delete/{INSTANCE_NAME}"
    requests.delete(url, headers=HEADERS)

def create_and_pair(phone_number):
    print("Limpando instância anterior (se existir)...")
    delete_instance()
    
    print(f"\nCriando nova instância '{INSTANCE_NAME}' e solicitando pareamento para {phone_number}...")
    
    url = f"{BASE_URL}/instance/create"
    payload = {
        "instanceName": INSTANCE_NAME,
        "token": "rocksfit-token-local",
        "qrcode": False,
        "integration": "WHATSAPP-BAILEYS",
        "number": phone_number
    }
    
    response = requests.post(url, headers=HEADERS, json=payload)
    
    if response.status_code in [200, 201]:
        data = response.json()
        print("\n✅ Instância criada com sucesso!")
        
        # A Evolution API 2.4.0+ retorna um 'pairingCode' se o 'number' for fornecido
        if data.get("pairingCode"):
            print(f"\n=========================================")
            print(f"👉 CÓDIGO DE PAREAMENTO: {data['pairingCode']}")
            print(f"=========================================\n")
            print("COMO PAREAR NO SEU CELULAR (O NÚMERO DA ACADEMIA):")
            print("1. Abra o WhatsApp.")
            print("2. Vá em 'Aparelhos Conectados' > 'Conectar um aparelho'.")
            print("3. Escolha 'Conectar com número de telefone'.")
            print("4. Digite o código acima.")
            print("5. Aguarde o WhatsApp sincronizar totalmente antes de tentar enviar mensagens.")
        else:
            print("Não retornou código. Verifique se o número está correto.")
    else:
        print(f"\n❌ Falha ao criar instância: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    phone = input("\n📱 Digite o seu número de WhatsApp de TESTE com DDI e DDD (Ex: 5584999999999): ")
    if phone:
        create_and_pair(phone.strip())
    else:
        print("Número inválido.")
