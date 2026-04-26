import socket

# Configuração da Porta que a Catraca costuma usar para enviar eventos
MINHA_PORTA_ESCUTA = 5000 

def escutar_placa():
    print("="*50)
    print("      ESCUTADOR DE EVENTOS (SNIFFER ROCKS FIT)")
    print("="*50)
    print(f"Ouvindo na porta {MINHA_PORTA_ESCUTA}...")
    print("Aguardando a placa enviar qualquer sinal (passe o dedo ou aproxime o cartao)...")

    # Tentamos tanto UDP quanto TCP
    try:
        # UDP (Mais comum para broadcast de placas)
        sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_udp.bind(('0.0.0.0', MINHA_PORTA_ESCUTA))
        sock_udp.settimeout(10)

        while True:
            try:
                data, addr = sock_udp.recvfrom(1024)
                print(f"\n[SINAL UDP RECEBIDO de {addr}]")
                print(f"Pacote Hex: {data.hex(' ')}")
                print(f"Pacote Txt: {data.decode('utf-8', errors='ignore')}")
            except socket.timeout:
                print(".", end="", flush=True)
                continue
    except Exception as e:
        print(f"\nErro ao iniciar escuta: {e}")

if __name__ == "__main__":
    escutar_placa()
