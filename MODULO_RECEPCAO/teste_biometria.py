import time
import sys
import socket

# Tenta importar bibliotecas do Windows para o U.are.U 4500
try:
    import win32com.client
    import pythoncom
except ImportError:
    print("\n[!] ERRO: Dependência 'pywin32' não encontrada.")
    print("Execute: pip install pywin32")
    sys.exit()

def testar_conexao_hardware():
    print("\n" + "="*60)
    print("  ROCKS FIT - TESTE DE HARDWARE BIOMÉTRICO (Digital Persona)")
    print("="*60)
    
    try:
        # Tenta instanciar o componente principal do SDK
        capture = win32com.client.Dispatch("DPFP.OneTouch.Capture.1")
        print("✅ SDK Digital Persona detectado com sucesso.")
        
        # Tenta verificar se há leitores conectados
        readers = win32com.client.Dispatch("DPFP.OneTouch.ReadersCollection.1")
        count = readers.Count
        
        if count == 0:
            print("❌ NENHUM LEITOR CONECTADO!")
            print("   Dica: Verifique o cabo USB e se o driver OneTouch está instalado.")
            return False
        
        print(f"✅ {count} leitor(es) encontrado(s).")
        for i in range(count):
            r = readers.Item(i+1) # Index do SDK começa em 1
            print(f"   -> Leitor {i+1}: {r.Description}")
            
        return True
    except Exception as e:
        print(f"❌ Falha ao inicializar SDK: {e}")
        return False

class TestEventHandler:
    def OnComplete(self, Reader, Sample):
        print("\n[⚡] DEDO CAPTURADO!")
        print("     O hardware está lendo corretamente.")
        print("     Aguardando 2 segundos para liberar o buffer...")
        time.sleep(2)
        print("\n     Pronto para novo teste ou feche a janela.")

def iniciar_teste_captura():
    print("\n[1] Iniciando loop de captura de teste...")
    try:
        handler = TestEventHandler()
        capture = win32com.client.DispatchWithEvents("DPFP.OneTouch.Capture.1", handler)
        capture.StartCapture()
        
        print("\n>>> COLOQUE O DEDO NO LEITOR PARA TESTAR <<<")
        print("(Pressione Ctrl+C para encerrar o teste)")
        
        while True:
            pythoncom.PumpWaitingMessages()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nTeste encerrado pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro durante a captura: {e}")

if __name__ == "__main__":
    if testar_conexao_hardware():
        iniciar_teste_captura()
    else:
        print("\nO hardware não pôde ser iniciado. O teste de captura foi cancelado.")
    
    input("\nPressione ENTER para sair...")
