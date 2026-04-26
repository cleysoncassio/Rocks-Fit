import socket

def capturar_comando_real():
    # O IP do seu computador na rede da catraca e 169.254.37.1
    # Vamos ouvir na porta 3000
    PORTA = 3000
    
    print("="*50)
    print("      O GRAMPO - CAPTURADOR DE PROTOCOLO")
    print("="*50)
    print(f"Ouvindo na porta {PORTA}...")
    print("INSTRUÇÕES:")
    print("1. Abra o Gerenciador Toletus.")
    print("2. MUDE O IP DA CATRACA PARA 169.254.37.1 no gerenciador.")
    print("3. Clique em LIBERAR no gerenciador.")
    
    # Tentamos tanto UDP quanto TCP
    sock_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_udp.bind(('0.0.0.0', PORTA))
    
    sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock_tcp.bind(('0.0.0.0', PORTA))
    sock_tcp.listen(1)
    sock_tcp.settimeout(1)

    print("\nAguardando comando do software Toletus...\n")

    try:
        while True:
            # 1. TENTA CAPTURAR UDP
            try:
                data_udp, addr_udp = sock_udp.recvfrom(1024)
                print(f"[COMANDO UDP CAPTURADO de {addr_udp}]")
                print(f"HEX: {data_udp.hex(' ')}")
                print(f"TXT: {data_udp.decode('utf-8', errors='ignore')}")
                print("-" * 30)
            except: pass

            # 2. TENTA CAPTURAR TCP
            try:
                conn, addr_tcp = sock_tcp.accept()
                with conn:
                    data_tcp = conn.recv(1024)
                    print(f"[COMANDO TCP CAPTURADO de {addr_tcp}]")
                    print(f"HEX: {data_tcp.hex(' ')}")
                    print(f"TXT: {data_tcp.decode('utf-8', errors='ignore')}")
                    print("-" * 30)
            except: pass

    except KeyboardInterrupt:
        print("\nGrampo encerrado.")
    finally:
        sock_udp.close()
        sock_tcp.close()

if __name__ == "__main__":
    capturar_comando_real()
