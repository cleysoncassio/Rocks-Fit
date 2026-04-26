import socket

CATRACA_IP = "169.254.37.150"
PORTA = 3000

# TESTES DE PRECISÃO (Onde fica o ID e o Sentido?)
TESTES = {
    "VAR_1 (ID 3 + Sentido 0)": b"lgu\x03\x00Liberou Entrada",
    "VAR_2 (Sentido 0 + ID 3)": b"lgu\x00\x03Liberou Entrada",
    "VAR_3 (Apenas Sentido 0)": b"lgu\x00Liberou Entrada",
    "VAR_4 (ID 0 + Sentido 0)": b"lgu\x00\x00Liberou Entrada",
}

def rodar_teste_mestre():
    print("--- TESTE MESTRE DE BYTES ---")
    
    for nome, pacote in TESTES.items():
        print(f"\nTestando {nome}...")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((CATRACA_IP, PORTA))
                s.sendall(pacote)
                
                try:
                    res = s.recv(1024)
                    print(f"✅ Resposta da Placa: {res.hex(' ')} | {res.decode('utf-8', errors='ignore')}")
                    if b"OK" in res:
                        print("⭐⭐⭐ ESTE É O COMANDO CORRETO! ⭐⭐⭐")
                except:
                    print("⚠️ Placa nao respondeu (mas aceitou o pacote)")
        except Exception as e:
            print(f"❌ Erro de conexao: {e}")

if __name__ == "__main__":
    rodar_teste_mestre()
    input("\nPressione ENTER para fechar...")
