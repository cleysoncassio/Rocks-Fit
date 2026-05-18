import os
import django
import json
import numpy as np
import shutil

# Configuração do Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings.development")
django.setup()

from blog.models import Aluno

def export_to_reception():
    print("🚀 [EXPORT] Iniciando exportação para o Módulo de Recepção...")
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RECEPTION_DIR = os.path.join(BASE_DIR, "MODULO_RECEPCAO")
    SYNC_FILE = os.path.join(RECEPTION_DIR, "ALUNOS_SYNC.json")
    FACES_DIR = os.path.join(RECEPTION_DIR, "BIOMETRIA_DATA", "faces")
    
    os.makedirs(FACES_DIR, exist_ok=True)
    
    alunos = Aluno.objects.all()
    lista_sync = []
    
    for a in alunos:
        # 1. Dados básicos para o JSON
        status = "INATIVO"
        vencimento = "SEM PLANO"
        if hasattr(a, 'acesso'):
            status = a.acesso.status_catraca.upper()
            venc = a.acesso.data_vencimento
            vencimento = venc.strftime('%d/%m/%Y') if venc else "SEM VENCIMENTO"
        
        # O Monitor do aluno espera que o foto_url seja acessível
        foto_url = None
        if a.foto:
            # Em desenvolvimento local, a foto está em /media/
            foto_url = a.foto.url
            
        lista_sync.append({
            'nome': a.nome_completo,
            'matricula': a.matricula,
            'status': status,
            'vencimento': vencimento,
            'foto_url': foto_url,
            'dias_restantes': a.acesso.dias_vencimento if hasattr(a, 'acesso') else 0
        })
        
        # 2. Exportar Embedding para .npy (Cache do Monitor)
        if a.facial_embedding:
            try:
                embedding_np = np.array(a.facial_embedding)
                npy_path = os.path.join(FACES_DIR, f"{a.matricula}.npy")
                np.save(npy_path, embedding_np)
                # print(f"✅ [NPY] {a.matricula} exportado.")
            except Exception as e:
                print(f"❌ [ERRO NPY] {a.matricula}: {e}")
                
    # Salvar JSON
    with open(SYNC_FILE, "w", encoding="utf-8") as f:
        json.dump(lista_sync, f, ensure_ascii=False, indent=4)
        
    print(f"✨ [EXPORT] Sincronização concluída: {len(lista_sync)} alunos exportados.")
    print(f"📂 Arquivo: {SYNC_FILE}")
    print(f"🖼️ Cache Facial: {FACES_DIR}")

if __name__ == "__main__":
    export_to_reception()
