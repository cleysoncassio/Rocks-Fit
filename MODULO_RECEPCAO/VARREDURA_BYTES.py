import socket

CATRACA_IP = "169.254.37.150"
PORTA = 3000

def varredura_total():
    print("--- VARREDURA DE BYTES (ID 0 e 3) ---")
    
    # Vamos testar o comando lgu com bytes de 0 a 5 logo depois
    for i in range(6):
        for j in range(3):
            # lgu + BYTE_I + BYTE_J + Texto
            pacote = b"lgu" + bytes([i]) + bytes([j]) + b"Liberou Entrada"
            print(f"Testando bytes: lgu \\x0{i} \\x0{j}...", end=" ")
            
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1.5)
                    s.connect((CATRACA_IP, PORTA))
                    s.sendall(pacote)
                    try:
                        res = s.recv(1024)
                        if res:
                            print(f"✅ RESPOSTA: {res.hex(' ')}")
                        else:
                            print("..")
                    except:
                        print("..")
            except:
                print("❌")

if __name__ == "__main__":
    varredura_total()
    input("\nFim do teste. Pressione ENTER...")
