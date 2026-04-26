import socket
import time

# Configurações da Placa
IP_CATRACA = "169.254.37.150"
PORTA = 3000

def monitorar_placa():
    print("="*50)
    print("      MONITOR DE HARDWARE (STATUS DA PLACA)")
    print("="*50)
    print(f"Alvo: {IP_CATRACA}:{PORTA}")
    print("Enviando comando de monitoramento (mcg)...")

    # Criamos um socket UDP (Muitas placas Toletus enviam status via UDP Broadcast)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', PORTA)) # Ouve na mesma porta que a placa fala
    sock.settimeout(5)

    try:
        while True:
            # Envia o "Keep Alive" ou "Poll" para a placa
            # lgu\x00 (ou mcg) costuma forçar uma resposta de status do hardware
            sock.sendto(b"mcg", (IP_CATRACA, PORTA))
            
            try:
                data, addr = sock.recvfrom(1024)
                print(f"\n[DADOS DA PLACA RECEBIDOS]")
                print(f"Status Bruto (Hex): {data.hex(' ')}")
                print(f"Status Texto: {data.decode('utf-8', errors='ignore')}")
                
                # Analise Rapida:
                if b"lguOK" in data: print(">> STATUS: Comando de Abertura Aceito!")
                if b"mcg" in data: print(">> STATUS: Placa Ativa e Respondendo (Heartbeat)")
                
            except socket.timeout:
                print(".", end="", flush=True)
            
            time.sleep(2) # Pergunta a cada 2 segundos

    except KeyboardInterrupt:
        print("\nMonitoramento encerrado.")
    except Exception as e:
        print(f"\nErro no monitor: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    monitorar_placa()
