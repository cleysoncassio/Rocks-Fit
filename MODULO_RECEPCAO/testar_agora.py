import cv2
import requests
import base64
import time

SITE_URL = "https://academiarocksfit.com.br"
SYNC_TOKEN = "rocksfit@2024"

def testar():
    print("🚀 INICIANDO TESTE AUTOMÁTICO DE RECONHECIMENTO...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Erro: Não consegui abrir a webcam (Index 0). Tentando Index 1...")
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print("❌ Erno: Nenhuma webcam encontrada.")
            return

    print("📸 Webcam aberta! Posicione seu rosto em 3 segundos...")
    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)

    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("❌ Erro ao capturar imagem.")
        return

    # Salva local para conferência
    cv2.imwrite("ultimo_teste.jpg", frame)
    print("✅ Foto capturada e salva como 'ultimo_teste.jpg'")

    # Converte para base64
    _, b = cv2.imencode('.jpg', frame)
    b64 = f"data:image/jpeg;base64,{base64.b64encode(b).decode('utf-8')}"

    print(f"📡 Enviando para {SITE_URL}...")
    try:
        r = requests.post(
            f"{SITE_URL}/api/face-check/", 
            data={'frame': b64, 'token': SYNC_TOKEN}, 
            timeout=15
        )
        
        if r.status_code == 200:
            d = r.json()
            print(f"\n✨ RECONHECIDO COM SUCESSO!")
            print(f"👤 Aluno: {d.get('nome')}")
            print(f"📝 Resultado: {d.get('mensagem')}")
        elif r.status_code == 404:
            print("\n❌ ALUNO NÃO ENCONTRADO NO BANCO DE DADOS.")
            print("Verifique se você tem foto no cadastro e se o status está ATIVO.")
        else:
            print(f"\n⚠️ Resposta do Servidor: {r.status_code} - {r.text}")
            
    except Exception as e:
        print(f"\n❌ ERRO DE CONEXÃO: {e}")
        print("Dica: Verifique se sua internet está ativa e se o site está acessível.")

if __name__ == "__main__":
    testar()
