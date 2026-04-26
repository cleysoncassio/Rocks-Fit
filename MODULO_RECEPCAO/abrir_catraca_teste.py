import socket
import sys

# CONFIGURAÇÕES
CATRACA_IP = "169.254.37.150"
CATRACA_PORTA = 5000

def testar_abertura():
    print(f"--- TESTE DE ABERTURA ROCKS FIT ---")
    print(f"Alvo: {CATRACA_IP}:{CATRACA_PORTA}")
    
    # Comando exato que funcionava
    comando = b"lgu\x00Liberou Entrada"
    
    try:
        print("Conectando...")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((CATRACA_IP, CATRACA_PORTA))
            
            print("Enviando comando de liberação...")
            s.sendall(comando)
            
            print("Aguardando resposta da placa...")
            resposta = s.recv(1024)
            
            print(f"✅ SUCESSO! A placa respondeu: {resposta.decode('utf-8', errors='ignore')}")
            print("A catraca deve ter liberado agora.")
            
    except Exception as e:
        print(f"❌ FALHA: {e}")
        print("\nVerificacoes:")
        print("1. O cabo de rede esta conectado?")
        print("2. O IP 169.254.37.150 esta correto?")
        print("3. O programa 'Toletus Gerenciador' esta FECHADO?")

if __name__ == "__main__":
    testar_abertura()
    input("\nPressione ENTER para fechar...")
