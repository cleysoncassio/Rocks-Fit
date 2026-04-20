import os
import django
import csv
import re
from datetime import datetime, date, timedelta
from decimal import Decimal

import sys

# Adicionar a raiz do projeto ao PYTHONPATH para encontrar o módulo 'sitio'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configuração do ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings.development")
django.setup()

from blog.models import Aluno, ControleAcesso, Plan

def clean_cpf(val):
    if not val: return ""
    clean = re.sub(r'\D', '', str(val))
    # Padding zeros if CPF has 10 digits
    if len(clean) == 10: clean = '0' + clean
    return clean

def parse_date(val):
    if not val: return None
    val = str(val).strip()
    if not val or val.lower() in ['nan', '', 'none', 'null']: return None
    
    # Try formats
    for fmt in ["%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"]:
        try:
            return datetime.strptime(val.split(' ')[0], fmt).date()
        except:
            continue
    return None

def get_rows(path):
    if path.endswith('.xlsx'):
        import openpyxl
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb.active
        for row in ws.iter_rows(values_only=True):
            yield [str(c) if c is not None else "" for c in row]
    else:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                yield row

def ingest_data():
    folder = 'temp'
    today = date.today()
    
    identities = {} # {nome_normalizado: {data}}
    
    # 1. Localizar e Carregar Identidades (clientes*.csv ou clientes*.xlsx)
    path_clientes = None
    for filename in os.listdir(folder):
        if filename.startswith('clientes') and (filename.endswith('.csv') or filename.endswith('.xlsx')):
            path_clientes = os.path.join(folder, filename)
            break
    
    if not path_clientes:
        print(f"Erro: Nenhum arquivo de 'clientes' encontrado na pasta '{folder}'.")
        return

    rows = get_rows(path_clientes)
    try:
        headers = next(rows)
    except StopIteration:
        print(f"Erro: Arquivo '{path_clientes}' está vazio.")
        return

    # Headers mapping
    try:
        idx_nome = headers.index('Nome')
        idx_email = headers.index('E-mail')
        idx_contrato = headers.index('Contrato')
        idx_tel = headers.index('Telefone')
        idx_cpf = headers.index('CPF')
        idx_nasc = headers.index('Data de nascimento')
        idx_sexo = headers.index('Sexo')
    except ValueError as e:
        print(f"Erro: Coluna não encontrada no cabeçalho: {e}")
        return
        
    for row in rows:
        if not row or len(row) <= max(idx_nome, idx_cpf): continue
        nome = row[idx_nome].strip()
        email = row[idx_email].strip()
        cpf = clean_cpf(row[idx_cpf])
        
        if not nome or (not cpf and not email): continue
        
        identities[nome.lower()] = {
            'nome': nome,
            'email': email,
            'cpf': cpf,
            'whatsapp': row[idx_tel].strip(),
            'data_nascimento': parse_date(row[idx_nasc]),
            'sexo': row[idx_sexo].strip()[0].upper() if row[idx_sexo] else 'O',
            'contrato_original': row[idx_contrato].strip(),
            'is_convenio': False,
            'vencimento': None
        }

    # 2. Carregar Validades e Identificar Convênios
    for filename in os.listdir(folder):
        if 'detalhes-contrato' in filename and (filename.endswith('.csv') or filename.endswith('.xlsx')):
            path = os.path.join(folder, filename)
            is_tp_wh = 'TotalPass' in filename or 'Wellhub' in filename
            
            rows_det = get_rows(path)
            try:
                h_det = next(rows_det)
                i_nome = h_det.index('Cliente')
                i_validade = h_det.index('Data de validade')
            except:
                continue
            
            for row in rows_det:
                if not row or len(row) <= max(i_nome, i_validade): continue
                cl_nome = row[i_nome].strip().lower()
                validade = parse_date(row[i_validade])
                
                if cl_nome in identities:
                    if is_tp_wh:
                        identities[cl_nome]['is_convenio'] = True
                    
                    curr = identities[cl_nome]['vencimento']
                    if validade and (not curr or validade > curr):
                        identities[cl_nome]['vencimento'] = validade

    # 3. Lógica Adicional e Ingestão
    final_new = 0
    final_upd = 0
    
    for k, d in identities.items():
        # Mensais s/ data -> +30 dias
        if not d['vencimento']:
            co = d['contrato_original'].upper()
            if 'MENSAL' in co or 'INDIVIDUAL' in co or 'AVULSO' in co:
                d['vencimento'] = today + timedelta(days=30)
        
        # Aluno logic
        aluno, created = Aluno.objects.update_or_create(
            cpf=d['cpf'],
            defaults={
                'nome_completo': d['nome'],
                'email': d['email'] or f"{d['cpf']}@rocksfit.com",
                'whatsapp': d['whatsapp'] or "0" * 11,
                'data_nascimento': d['data_nascimento'],
                'sexo': d['sexo'] if d['sexo'] in ['M', 'F', 'O'] else 'O',
                'is_convenio': d['is_convenio'],
                'status': 'ATIVO'
            }
        )
        
        # Acesso logic
        venc = d['vencimento']
        # Se for convênio (TotalPass/Wellhub) e não tem data de validade na planilha,
        # geralmente a validação é feita via App, mas aqui liberaremos por 30 dias se ativo.
        if d['is_convenio'] and not venc:
            venc = today + timedelta(days=30)
            
        status_c = 'liberado' if venc and venc >= today else 'bloqueado'
        
        ControleAcesso.objects.update_or_create(
            aluno=aluno,
            defaults={
                'data_vencimento': venc,
                'status_catraca': status_c
            }
        )
        
        if created: final_new += 1
        else: final_upd += 1

    print(f"IMPORTAÇÃO FINALIZADA:")
    print(f"- Sucesso: {final_new} novos alunos.")
    print(f"- Atualizados: {final_upd} registros.")

if __name__ == "__main__":
    ingest_data()
