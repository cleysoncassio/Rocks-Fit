import time
import socket
import sys

# Tenta importar bibliotecas do Windows para o U.are.U 4500
try:
    import win32com.client
    import pythoncom
except ImportError:
    print("ERRO: Biblioteca pywin32 não encontrada.")
    print("Rode: pip install pywin32")
    sys.exit()

# --- CONFIGURAÇÕES ---
HOST = '127.0.0.1'  # Envia para o ponte_rocksfit.py na mesma máquina
PORT = 5000         # Porta padrão do sistema Rocks Fit

def enviar_para_sistema(digital_id):
    """ Envia o ID da digital via Socket para o sistema principal """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect((HOST, PORT))
            # O sistema espera o formato "TAG|ID" ou apenas "ID"
            s.sendall(f"BIO|{digital_id}".encode('utf-8'))
            print(f"✅ Digital {digital_id} enviada com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao enviar para o sistema: {e}")

class EventHandler:
    """ Captura eventos do Leitor Digital Persona """
    def OnComplete(self, Reader, Sample):
        print("Finger captured! Processing...")
        # Aqui o SDK processaria a digital. 
        # Como este leitor usa comparação 1:N no servidor ou local,
        # geramos um hash ou usamos o serial.
        # Para simplificar na Rocks Fit, usamos o ID unico do evento ou tag.
        enviar_para_sistema("DP-" + str(int(time.time())))

def iniciar_leitor():
    print("="*50)
    print("  ROCKS FIT - INTERFACE U.ARE.U 4500")
    print("="*50)
    
    try:
        # Verifica se há leitores antes de iniciar
        readers = win32com.client.Dispatch("DPFP.OneTouch.ReadersCollection.1")
        if readers.Count == 0:
            print("❌ ERRO: Nenhum leitor biométrico USB detectado.")
            print("Verifique o cabo e o driver OneTouch SDK.")
            input("Pressione Enter para sair...")
            sys.exit()

        print(f"✅ Hardware detectado: {readers.Item(1).Description}")
        print("Aguardando leitura de digital...")

        # Inicializa o Objeto do SDK Digital Persona
        capture = win32com.client.DispatchWithEvents("DPFP.OneTouch.Capture.1", EventHandler)
        capture.StartCapture()
        
        while True:
            pythoncom.PumpWaitingMessages()
            time.sleep(0.05)
    except Exception as e:
        print(f"❌ Erro ao iniciar hardware: {e}")
        print("Verifique se o OneTouch SDK está instalado corretamente.")
        input("Pressione Enter para sair...")

if __name__ == "__main__":
    iniciar_leitor()
