import requests

BASE_URL = "http://localhost:8080"
GLOBAL_API_KEY = "429683C4C977415CBEE243405C76100E"
INSTANCE_NAME = "Rocksfit-business"

HEADERS = {
    "apikey": GLOBAL_API_KEY,
    "Content-Type": "application/json"
}

def send_test_message(phone_number):
    print(f"\nEnviando mensagem de teste para {phone_number}...")
    url = f"{BASE_URL}/message/sendText/{INSTANCE_NAME}"
    payload = {
        "number": phone_number,
        "text": "🤖 *Mensagem de Teste Local*\nOlá! A sua Evolution API está conectada com sucesso ao seu ambiente de desenvolvimento do Rocks-Fit."
    }
    
    response = requests.post(url, headers=HEADERS, json=payload)
    
    if response.status_code in [200, 201]:
        print("✅ Mensagem enviada com sucesso!")
        print(response.json())
    else:
        print(f"❌ Falha ao enviar mensagem: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    phone = input("\n📱 Digite o número de WhatsApp de destino com DDI e DDD (Ex: 5584999999999): ")
    if phone:
        send_test_message(phone.strip())
    else:
        print("Número inválido.")
