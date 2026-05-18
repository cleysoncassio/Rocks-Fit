import os
import django
import requests
import json
from datetime import datetime
from django.core.files.base import ContentFile

# Configuração do Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings.development")
django.setup()

from blog.models import Aluno, ControleAcesso

def sync_crm():
    SITE_URL = "https://academiarocksfit.com.br"
    SYNC_TOKEN = "Rocksfit@2024"
    
    print(f"📡 Conectando ao CRM: {SITE_URL}...")
    
    try:
        url = f"{SITE_URL}/api/catraca-sync/?token={SYNC_TOKEN}"
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Erro na API: {response.status_code}")
            return
            
        data = response.json()
        alunos_json = data.get('alunos', [])
        print(f"✅ Recebidos {len(alunos_json)} alunos.")
        
        status_map = {
            "LIBERADO": "liberado",
            "ATIVO": "liberado",
            "INATIVO": "bloqueado",
            "SUSPENSO": "bloqueado",
            "CANCELADO": "bloqueado",
            "AGUARDANDO_PAGAMENTO": "aguardando_pagamento",
            "AGUARDANDO_BIOMETRIA": "aguardando_biometria"
        }
        
        for a_data in alunos_json:
            nome = a_data.get('nome')
            cpf = a_data.get('cpf')
            matricula = a_data.get('matricula')
            foto_url = a_data.get('foto') or a_data.get('foto_url')
            
            if not cpf or not nome:
                continue
                
            print(f"👤 Sincronizando: {nome} ({matricula})...")
            
            # 1. Atualizar Aluno
            aluno, created = Aluno.objects.update_or_create(
                cpf=cpf,
                defaults={
                    'nome_completo': nome,
                    'matricula': matricula,
                }
            )
            
            # 2. Baixar Foto se disponível
            if foto_url:
                try:
                    full_foto_url = foto_url if foto_url.startswith("http") else f"{SITE_URL}{foto_url}"
                    print(f"  📸 Baixando foto: {full_foto_url}")
                    img_resp = requests.get(full_foto_url, timeout=10)
                    if img_resp.status_code == 200:
                        file_name = f"aluno_{matricula}.jpg"
                        aluno.foto.save(file_name, ContentFile(img_resp.content), save=True)
                        print(f"  ✅ Foto salva localmente.")
                except Exception as img_err:
                    print(f"  ⚠️ Erro ao baixar foto: {img_err}")
            
            # 3. Atualizar Controle de Acesso
            vencimento_str = a_data.get('vencimento')
            data_vencimento = None
            if vencimento_str and vencimento_str not in ["SEM PLANO", "SEM VENCIMENTO"]:
                try:
                    data_vencimento = datetime.strptime(vencimento_str, "%d/%m/%Y").date()
                except ValueError:
                    # Tenta formato americano se falhar
                    try:
                        data_vencimento = datetime.strptime(vencimento_str, "%Y-%m-%d").date()
                    except:
                        pass

            status_catraca = status_map.get(a_data.get('status'), 'bloqueado')
            ControleAcesso.objects.update_or_create(
                aluno=aluno,
                defaults={
                    'status_catraca': status_catraca,
                    'data_vencimento': data_vencimento
                }
            )
            
        print("\n✨ Sincronização completa!")
        
    except Exception as e:
        print(f"❌ Erro crítico no sync: {e}")

if __name__ == "__main__":
    sync_crm()
