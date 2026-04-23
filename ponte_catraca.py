import socket
import time
import requests

# --- CONFIGURAÇÕES DA ACADEMIA ---
# O IP que você usa para acessar o site (ex: https://rocksfit.com)
SITE_URL = "https://academiarocksfit.com.br" 
API_ENDPOINT = f"{SITE_URL}/api/catraca-polling/"

# --- CONFIGURAÇÕES DA CATRACA ---
CATRACA_IP = "169.254.37.150"
CATRACA_PORTA = 3000 
# O comando exato: lgu + Byte Nulo + Mensagem
COMANDO_ABRIR = b"lgu\x00Liberou Entrada"

print(f"--- Ponte Catraca Rocks Fit Ativa ---")
print(f"Monitorando: {API_ENDPOINT}")
print(f"Alvo Catraca: {CATRACA_IP}:{CATRACA_PORTA}")

def enviar_comando_catraca():
    try:
        # Abre conexão TCP com a Toletus
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((CATRACA_IP, CATRACA_PORTA))
            s.sendall(COMANDO_ABRIR)
            resposta = s.recv(1024)
            print(f"Catraca respondeu: {resposta.decode('utf-8', errors='ignore')}")
            return True
    except Exception as e:
        print(f"Erro ao falar com a catraca: {e}")
        return False

        else:
            print(f"⚠ Erro na API: {response.status_code} (Verifique o Token)")
    except Exception as e:
        print(f"⚠ Erro de conexão com o site: {e}")

# Loop Infinito de Monitoramento (Polling)
try:
    while True:
        # Adicionado o Token de Sincronização
        API_ENDPOINT_AUTH = f"{API_ENDPOINT}?token=rocksfit@2024"
        try:
            response = requests.get(API_ENDPOINT_AUTH, timeout=10)
            if response.status_code == 200:
                data = response.json()
                liberacoes = data.get('liberacoes', [])
                
                for lib in liberacoes:
                    print(f"📢 Liberando para: {lib['nome']} (CPF: {lib['cpf']})")
                    if enviar_comando_catraca():
                        print(f"✅ Catraca aberta com sucesso!")
                    else:
                        print(f"❌ Falha ao abrir catraca.")
            else:
                print(f"⚠ Erro na API: {response.status_code}")
        except Exception as e:
            print(f"⚠ Erro de polling: {e}")
            
        time.sleep(3) 
except KeyboardInterrupt:
    print("\nEncerrando monitoramento...")
