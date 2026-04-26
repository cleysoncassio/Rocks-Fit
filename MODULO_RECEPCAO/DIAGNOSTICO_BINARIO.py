import socket
import time

# IP E BROADCAST
IP_CATRACA = "169.254.37.150"
IP_BROADCAST = "169.254.255.255"
PORTA = 3000

# PACOTES BINÁRIOS PUROS (O "SEGREDO" DAS PLACAS)
TESTES = {
    "UDP_ID3_ENTRADA": b"lgu\x03\x00Liberou Entrada",
    "UDP_ID3_SAIDA":   b"lgu\x03\x01Liberou Saida",
    "UDP_ID0_UNIVERSAL": b"lgu\x00\x00Liberou Entrada",
    "UDP_LITE_NET_V2": b"lgu\x00Liberou Entrada\r\n",
    "UDP_STX_ETX": b"\x02lgu\x03\x00Liberou Entrada\x03"
}

def rodar_binario():
    print("="*50)
    print("      DIAGNÓSTICO BINÁRIO (UDP MASTER)")
    print("="*50)
    print(f"Lançando comandos para {IP_CATRACA} e {IP_BROADCAST}...")

    # Criamos um socket UDP com permissao de Broadcast
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(1)

    for nome, pacote in TESTES.items():
        print(f"\nTentando {nome}...", end=" ", flush=True)
        try:
            # Envia via UDP (que nao precisa de conexao aberta)
            sock.sendto(pacote, (IP_CATRACA, PORTA))
            time.sleep(0.05)
            sock.sendto(pacote, (IP_BROADCAST, PORTA))
            print("✔ DISPARADO")
        except Exception as e:
            print(f"❌ ERRO: {e}")
        
        time.sleep(0.5)

    sock.close()
    print("\n" + "="*50)
    print("Verifique se a catraca girou agora.")
    print("Lembre-se de fechar o Gerenciador Toletus antes de testar.")

if __name__ == "__main__":
    rodar_binario()
    input("\nPressione ENTER para fechar...")
