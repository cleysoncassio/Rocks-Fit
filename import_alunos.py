import os
import django
import json
from datetime import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings")
django.setup()

from blog.models import Aluno, ControleAcesso

def import_alunos():
    caminho_json = "rks-catraca/alunos_local.json"
    if not os.path.exists(caminho_json):
        print(f"Erro: Arquivo {caminho_json} não encontrado.")
        return

    with open(caminho_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    status_map = {
        "LIBERADO": "liberado",
        "INATIVO": "bloqueado",
        "AGUARDANDO_PAGAMENTO": "aguardando_pagamento",
        "AGUARDANDO_BIOMETRIA": "aguardando_biometria"
    }

    alunos_json = data.get('alunos', [])
    for a_data in alunos_json:
        # 1. Criar ou Atualizar Aluno
        # Nota: Usamos get_or_create pelo CPF para evitar duplicatas
        aluno, created = Aluno.objects.update_or_create(
            cpf=a_data['cpf'],
            defaults={
                'nome_completo': a_data['nome'],
                'matricula': a_data['matricula'],
                'email': f"{a_data['cpf']}@rocksfit.com", # Placeholder
                'whatsapp': '00000000000' # Placeholder
            }
        )
        
        if created:
            print(f"Aluno criado: {aluno.nome_completo}")
        else:
            print(f"Aluno atualizado: {aluno.nome_completo}")

        # 2. Configurar Controle de Acesso
        vencimento_str = a_data.get('vencimento')
        data_vencimento = None
        if vencimento_str and vencimento_str not in ["SEM PLANO", "SEM VENCIMENTO"]:
            try:
                data_vencimento = datetime.strptime(vencimento_str, "%d/%m/%Y").date()
            except ValueError:
                print(f"Erro ao formatar data: {vencimento_str}")

        status_catraca = status_map.get(a_data['status'], 'bloqueado')

        acesso, ac_created = ControleAcesso.objects.update_or_create(
            aluno=aluno,
            defaults={
                'status_catraca': status_catraca,
                'data_vencimento': data_vencimento
            }
        )
        
        if ac_created:
            print(f"  Acesso configurado: {status_catraca} (Venc: {data_vencimento})")
        else:
            print(f"  Acesso atualizado: {status_catraca} (Venc: {data_vencimento})")

if __name__ == "__main__":
    import_alunos()
    print("\nImportação de alunos concluída com sucesso!")
