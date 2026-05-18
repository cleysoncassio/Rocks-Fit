import os
import django

# Define o sinal de pular sinais
os.environ['SKIP_SIGNALS'] = '1'

# Configuração do Django PRIMEIRO
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sitio.settings.development')
django.setup()

# Importa DeepFace DEPOIS do Django
from deepface import DeepFace
from blog.models import Aluno

def rebuild_index():
    print("🚀 Iniciando Reconstrução do Índice Biométrico (ArcFace)...")
    # Usa list() para garantir que a conexão com o banco não fique aberta durante o processamento pesado se for o caso
    alunos = list(Aluno.objects.all())
    total = len(alunos)
    processados = 0
    erros = 0

    print(f"📊 Total de alunos a processar: {total}")

    for aluno in alunos:
        if not aluno.foto:
            print(f"⏩ [SKIP] {aluno.nome_completo} ({aluno.matricula}) - Sem foto.")
            continue
        
        try:
            img_path = aluno.foto.path
            if not os.path.exists(img_path):
                print(f"❌ [ERRO] Arquivo não encontrado: {img_path}")
                erros += 1
                continue

            print(f"🧠 [PROCESSANDO] {aluno.nome_completo}...")
            
            # Gera embedding usando ArcFace + RetinaFace
            results = DeepFace.represent(
                img_path=img_path,
                model_name="ArcFace",
                detector_backend="retinaface",
                enforce_detection=True,
                align=True
            )

            if results and len(results) > 0:
                embedding = results[0]["embedding"]
                aluno.facial_embedding = embedding
                aluno.save()
                processados += 1
                print(f"✅ [SUCESSO] {aluno.nome_completo} indexado.")
            else:
                print(f"⚠️ [AVISO] Nenhum rosto detectado na foto de {aluno.nome_completo}.")
                erros += 1

        except Exception as e:
            print(f"❌ [FALHA] Erro ao processar {aluno.nome_completo}: {e}")
            erros += 1

    print(f"\n=== RELATÓRIO FINAL ===")
    print(f"Total de Alunos: {total}")
    print(f"Indexados com Sucesso: {processados}")
    print(f"Falhas/Erros: {erros}")
    print("========================")

if __name__ == "__main__":
    rebuild_index()
