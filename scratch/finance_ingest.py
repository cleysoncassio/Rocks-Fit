import os
import django
import csv
import re
from decimal import Decimal
from datetime import datetime

import sys

# Adicionar a raiz do projeto ao PYTHONPATH para encontrar o módulo 'sitio'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configuração do ambiente Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings.production")
django.setup()

from blog.models import Aluno, PagamentoHistorico, CaixaTurno, TransacaoCaixa, User, Plan

def clean_money(val):
    if not val or str(val).lower() == 'nan': return Decimal('0.00')
    val = str(val).replace('R$', '').replace('.', '').replace(',', '.').strip()
    try: return Decimal(val)
    except: return Decimal('0.00')

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

def ingest_finance():
    folder = 'temp'
    vendas_files = [f for f in os.listdir(folder) if 'Vendas' in f and (f.endswith('.csv') or f.endswith('.xlsx'))]
    
    # 1. Garantir um Operador de Caixa (Admin)
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("Erro: Nenhum usuário administrador encontrado para abrir o caixa.")
        return

    # 2. Abrir um Turno de Caixa para a Importação
    turno, _ = CaixaTurno.objects.get_or_create(
        operador=admin_user,
        status='ABERTO',
        defaults={'saldo_inicial': 0}
    )

    p_count = 0
    t_count = 0
    
    for filename in vendas_files:
        path = os.path.join(folder, filename)
        rows = get_rows(path)
        try:
            headers = next(rows)
        except StopIteration:
            continue

        try:
            idx_cliente = headers.index('Cliente')
            idx_desc = headers.index('Descrição')
            idx_valor = headers.index('Valor')
            idx_dinheiro = headers.index('Dinheiro')
            idx_debito = headers.index('Cartão de débito')
            idx_credito = headers.index('Cartão de crédito')
            idx_boleto = headers.index('Boleto')
        except ValueError as e:
            print(f"Erro no cabeçalho de {filename}: {e}")
            continue
            
        for row in rows:
            if not row or len(row) <= max(idx_cliente, idx_boleto): continue
            
            nome_cliente = row[idx_cliente].strip()
            valor_total = clean_money(row[idx_valor])
            descricao = row[idx_desc].strip()
                
                if valor_total <= 0: continue
                
                # Buscar Aluno
                aluno = Aluno.objects.filter(nome_completo__iexact=nome_cliente).first()
                if not aluno:
                    # Tentar busca parcial ou ignorar se não achar
                    continue

                # 3. Criar Histórico de Pagamento
                pag = PagamentoHistorico.objects.create(
                    aluno=aluno,
                    valor=valor_total,
                    status='pago',
                    metodo_pagamento='Planilha Import'
                )
                p_count += 1
                
                # 4. Criar Transações de Caixa por Método
                v_din = clean_money(row[idx_dinheiro])
                v_deb = clean_money(row[idx_debito])
                v_cre = clean_money(row[idx_credito])
                v_bol = clean_money(row[idx_boleto])
                
                metodos = [
                    (v_din, 'DINHEIRO'),
                    (v_deb, 'DEBITO'),
                    (v_cre, 'CREDITO'),
                    (v_bol, 'PIX') # Assumindo Boleto/Outros como PIX na falta de coluna específica
                ]
                
                for valor, met_key in metodos:
                    if valor > 0:
                        TransacaoCaixa.objects.create(
                            caixa=turno,
                            tipo='ENTRADA',
                            origem='MANUAL',
                            metodo=met_key,
                            descricao=f"Pagamento Aluno: {aluno.nome_completo} ({descricao})",
                            valor=valor
                        )
                        t_count += 1

    print(f"INGESTÃO FINANCEIRA CONCLUÍDA:")
    print(f"- Pagamentos vinculados a alunos: {p_count}")
    print(f"- Lançamentos realizados no caixa: {t_count}")

if __name__ == "__main__":
    ingest_finance()
