import socket
import time

CATRACA_IP = "169.254.37.150"
PORTA = 3000

def chute_de_origem():
    print("="*50)
    print("      TESTE DE PORTA DE ORIGEM (PORTA 3000)")
    print("="*50)
    
    # O comando binário lgu + sentido
    comando = b"lgu\x00Liberou Entrada"
    
    try:
        # Criamos o socket e AMARRAMOS ele na porta 3000 do seu PC
        # Isso simula exatamente o que o Gerenciador Toletus faz
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            s.bind(('', 3000)) # Tenta usar a porta 3000 para sair
        except:
            print("A porta 3000 do seu PC ja esta em uso. FECHE O GERENCIADOR TOLETUS!")
            return

        s.settimeout(3)
        print(f"Conectando a {CATRACA_IP} usando a porta de origem 3000...")
        s.connect((CATRACA_IP, PORTA))
        
        print("Enviando comando...")
        s.sendall(comando)
        
        resposta = s.recv(1024)
        print(f"✅ SUCESSO! Resposta: {resposta.decode('utf-8', errors='ignore')}")
        s.close()
        
    except Exception as e:
        print(f"❌ Falha: {e}")

if __name__ == "__main__":
    chute_de_origem()
    input("\nPressione ENTER para fechar...")
