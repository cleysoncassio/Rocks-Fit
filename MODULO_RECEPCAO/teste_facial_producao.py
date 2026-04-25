import requests
import base64
import os
import cv2

# Configurações de Produção
SITE_URL = "https://academiarocksfit.com.br"
SYNC_TOKEN = "rks_fit_2025_secure_sync_token"

def simular_facial(caminho_foto):
    print(f"--- SIMULADOR DE RECONHECIMENTO FACIAL (PRODUÇÃO) ---")
    
    if not os.path.exists(caminho_foto):
        print(f"❌ Erro: Foto {caminho_foto} não encontrada.")
        return

    # 1. Carregar e codificar a imagem
    with open(caminho_foto, "rb") as image_file:
        b64 = f"data:image/jpeg;base64,{base64.b64encode(image_file.read()).decode('utf-8')}"

    # 2. Enviar para a API de Produção
    print(f"📡 Enviando frame para {SITE_URL}...")
    try:
        r = requests.post(
            f"{SITE_URL}/api/face-check/", 
            data={'frame': b64, 'token': SYNC_TOKEN}, 
            timeout=10
        )
        
        if r.status_code == 200:
            dados = r.json()
            print(f"\n✅ ALUNO IDENTIFICADO!")
            print(f"👤 Nome: {dados.get('nome')}")
            print(f"📝 Mensagem: {dados.get('mensagem')}")
            print(f"🔓 SIMULAÇÃO: Enviando comando 'abrir_catraca'...")
            print(f"   [COMANDO TCP]: b'lgu\\x00' -> IP 169.254.37.150")
        elif r.status_code == 404:
            print(f"\n❌ ERRO: Rosto não identificado no banco de dados de produção.")
            print(f"Dica: Verifique se o aluno está como ATIVO e tem foto cadastrada.")
        else:
            print(f"\n⚠️ Falha na API: {r.status_code} - {r.text}")
            
    except Exception as e:
        print(f"❌ Erro de conexão com o servidor: {e}")

if __name__ == "__main__":
    # Tenta usar a foto do primeiro aluno que encontrar na pasta se existir
    # Ou use um caminho específico: fotos/aluno_teste.jpg
    print("Para testar, coloque o caminho de uma foto de rosto abaixo:")
    foto = input("Caminho da foto (ex: foto_teste.jpg): ").strip()
    simular_facial(foto)
