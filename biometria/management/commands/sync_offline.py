import os
import time
import base64
import requests
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "Reenvia frames capturados offline para a API de Biometria quando a conexão é restabelecida."

    def handle(self, *args, **options):
        offline_dir = "BIOMETRIA_DATA/offline_queue"
        api_url = "http://localhost:8000/api/biometria/verificar/" # Ajuste se o servidor rodar em outra porta/host
        
        self.stdout.write(self.style.SUCCESS(f"🚀 Iniciando worker de sincronização offline em: {offline_dir}"))

        if not os.path.exists(offline_dir):
            os.makedirs(offline_dir, exist_ok=True)

        while True:
            try:
                files = sorted(os.listdir(offline_dir))
                if not files:
                    time.sleep(5)
                    continue

                for filename in files:
                    if not filename.endswith(".jpg"):
                        continue
                    
                    path = os.path.join(offline_dir, filename)
                    
                    try:
                        with open(path, "rb") as f:
                            img_data = f.read()
                            img_b64 = base64.b64encode(img_data).decode('utf-8')
                        
                        resp = requests.post(
                            api_url,
                            json={"image": img_b64},
                            timeout=10
                        )
                        
                        if resp.status_code == 200:
                            data = resp.json()
                            mat = data.get("matricula")
                            if mat and mat != "NO_MATCH":
                                self.stdout.write(self.style.SUCCESS(f"✅ [SYNC] Sincronizado: {mat} (Arquivo: {filename})"))
                                # Aqui você pode opcionalmente registrar em um log de acesso real se desejar
                            else:
                                self.stdout.write(self.style.WARNING(f"ℹ️ [SYNC] Processado sem match: {filename}"))
                            
                            os.remove(path)
                        else:
                            self.stdout.write(self.style.ERROR(f"❌ [SYNC] Erro na API ({resp.status_code}): {filename}"))
                            time.sleep(2) # Espera um pouco antes de tentar o próximo se deu erro de servidor

                    except requests.exceptions.RequestException as e:
                        # Falha de conexão real (servidor offline)
                        self.stdout.write(self.style.WARNING(f"📡 [SYNC] Servidor indisponível, aguardando... ({e})"))
                        time.sleep(10)
                        break # Sai do loop de arquivos e volta para o loop principal
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"⚠️ [SYNC] Erro ao processar {filename}: {e}"))
                        time.sleep(1)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"☢️ [SYNC] Erro crítico no worker: {e}"))
                time.sleep(5)
            
            time.sleep(2)
