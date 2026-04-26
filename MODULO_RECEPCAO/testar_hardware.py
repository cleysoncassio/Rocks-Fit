import socket
import time

IP = "169.254.37.150"
PORTA = 3000

print("-" * 50)
print(f"DEBUGGER DE HARDWARE ROCKS-FIT - FASE 2 (UDP & BINARY)")
print("-" * 50)

# Comandos mais "agressivos" de baixo nível
comandos_binarios = {
    "BYTE PURO 1": bytes([0x01]),
    "BYTE PURO 0": bytes([0x00]),
    "ABRIR TXT": b"ABRIR",
    "RELE 1": b"RELE1",
    "TCP ALIVE": b"{\"cmd\":\"open\",\"port\":1}" # Formato JSON que algumas usam
}

print(f"\n--- TESTANDO VIA UDP (Muitas placas usam isso) ---")
for nome, cmd in comandos_binarios.items():
    print(f"[UDP] Testando {nome}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # MODO UDP
        sock.settimeout(2)
        sock.sendto(cmd, (IP, PORTA))
        print("✅ Pacote UDP disparado!")
        sock.close()
    except Exception as e:
        print(f"❌ Erro UDP: {e}")
    time.sleep(0.5)

print(f"\n--- TESTANDO VIA TCP BINARIO ---")
for nome, cmd in comandos_binarios.items():
    print(f"[TCP] Testando {nome}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect((IP, PORTA))
            s.sendall(cmd)
            print("✅ Enviado!")
    except Exception as e:
        print(f"❌ Erro TCP: {e}")
    time.sleep(0.5)

print("\nAlgum desses deu sinal de vida na catraca?")
input("Pressione ENTER para sair...")
