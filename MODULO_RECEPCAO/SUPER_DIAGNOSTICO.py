import socket
import time

# CONFIGURAÇÕES DA PLACA
IP = "169.254.37.150"
PORTAS = [3000, 5000, 8000, 9000, 1000]

# FORMATOS DE COMANDO
COMANDOS = {
    "TOLETUS BINARIO": b"lgu\x00Liberou Entrada",
    "TOLETUS ASCII": b"lgu0Liberou Entrada",
    "PULSO SIMPLES (0)": b"0",
    "PULSO SIMPLES (1)": b"1",
    "STX/ETX FORMAT": b"\x02lgu\x00Liberou Entrada\x03",
    "KEEP ALIVE (mcg)": b"mcg"
}

def rodar_teste():
    print("="*50)
    print("      SUPER DIAGNÓSTICO DE HARDWARE ROCKS FIT")
    print("="*50)
    print(f"Alvo: {IP}")
    print("Iniciando varredura profunda...\n")

    for porta in PORTAS:
        print(f"\n>>> TESTANDO PORTA: {porta} <<<")
        for nome, cmd in COMANDOS.items():
            print(f" Tentando {nome}...", end=" ", flush=True)
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(3)
                    s.connect((IP, porta))
                    s.sendall(cmd)
                    
                    # Tenta ler a resposta com insistencia
                    time.sleep(0.2)
                    try:
                        resposta = s.recv(1024)
                        if not resposta:
                            # Tenta uma segunda leitura caso a primeira falhe
                            resposta = s.recv(1024)
                        
                        print("✅ CONECTADO!")
                        print(f"   [Resposta Hex  ]: {resposta.hex(' ')}")
                        print(f"   [Resposta Texto]: {resposta.decode('utf-8', errors='ignore')}")
                    except socket.timeout:
                        print("⚠️ TIMEOUT (Sem resposta da placa)")
                        
                        if b"OK" in resposta or len(resposta) > 0:
                            print("   ⭐ A placa RECONHECEU este formato!")
                    except socket.timeout:
                        print("⚠️ TIMEOUT (Enviado, mas placa não respondeu)")
                    except Exception as e:
                        print(f"❌ ERRO LEITURA: {e}")
            except ConnectionRefusedError:
                print("❌ RECUSADO (Placa não está ouvindo nesta porta)")
            except socket.timeout:
                print("❌ TIMEOUT (IP inacessível nesta porta)")
            except Exception as e:
                print(f"❌ ERRO CONEXÃO: {e}")
            
            time.sleep(0.1)

    print("\n" + "="*50)
    print("Teste finalizado. Verifique se a catraca girou em algum momento.")
    print("="*50)

if __name__ == "__main__":
    rodar_teste()
    input("\nPressione ENTER para fechar o diagnóstico...")
