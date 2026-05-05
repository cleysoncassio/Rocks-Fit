import os
import requests
import json
from datetime import date, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Q
from .models import Aluno, PagamentoHistorico, AcessoLog, GymSetting, AnaliseGeralIA, AcaoIA

def analisar_dados_ia():
    settings = GymSetting.objects.first()
    # Prioridade para o banco de dados, depois env
    api_key = (settings.ai_api_key if settings and settings.ai_api_key else None) or os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        return {"error": "API Key não configurada. Defina em Configurações ou no arquivo .env (OPENROUTER_API_KEY)."}

    # 1. Coleta de Dados Reais
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    
    total_alunos = Aluno.objects.count()
    ativos = Aluno.objects.filter(status='ATIVO').count()
    inativos = Aluno.objects.filter(status='INATIVO').count()
    
    faturamento_mes = PagamentoHistorico.objects.filter(
        status='pago', 
        data_pagamento__date__gte=inicio_mes
    ).aggregate(Sum('valor'))['valor__sum'] or 0
    
    # Churn Risk: Alunos ativos que não acessaram nos últimos 10 dias
    dez_dias_atras = timezone.now() - timedelta(days=10)
    alunos_com_acesso_recente = AcessoLog.objects.filter(
        data_hora__gte=dez_dias_atras
    ).values_list('aluno_id', flat=True).distinct()
    
    alunos_em_risco = Aluno.objects.filter(
        status='ATIVO'
    ).exclude(
        id__in=alunos_com_acesso_recente
    ).count()

    # Contexto para a IA
    dados_contexto = {
        "data_atual": hoje.strftime('%Y-%m-%d'),
        "metricas": {
            "total_alunos": total_alunos,
            "ativos": ativos,
            "inativos": inativos,
            "faturamento_mes_atual": float(faturamento_mes),
            "alunos_em_risco_churn": alunos_em_risco,
            "mrr_estimado": float(faturamento_mes),
        },
        "vencimentos_proximos": Aluno.objects.filter(
            acesso__data_vencimento__range=[hoje, hoje + timedelta(days=7)]
        ).count()
    }

    # System Prompt conforme solicitado pelo usuário
    prompt_sistema = settings.ai_system_prompt if settings and settings.ai_system_prompt else """
# IDENTITY & ROLE
Você é o "RKS Master IA", o Diretor Geral de Inteligência Artificial do CRM da academia 'Rocks Fit'. Você possui conhecimento nível sênior em: Finanças Corporativas, Marketing Digital, Gestão de Tráfego, Publicidade para o nicho Fitness e Análise Preditiva de Dados.

# CONTEXTO DE VENDAS E PRECIFICAÇÃO (BASE PARA CAMPANHAS)
Ao criar campanhas de aquisição ou mensagens de retenção, utilize os seguintes dados reais da Rocks Fit:
- Pagamento PIX: R$ 75,00 (Foco: Menor preço, desconto, urgência).
- Pagamento Cartão Recorrente: R$ 78,50 (Foco: Facilidade, não compromete o limite do cartão).
- Diferenciais da Marca: Flexibilidade de horários, professores qualificados, ambiente acolhedor (sem julgamentos).
- Personalização de Oferta: Ofertas de saúde focam em cuidado/longevidade; ofertas de estética focam em resultado/transformação.

# OBJETIVO PRINCIPAL
Sua missão é analisar o histórico de funcionamento da academia (dados fornecidos no prompt do usuário/sistema), prever evasão de alunos (churn), analisar a saúde financeira e gerar um relatório diário de ações estratégicas. Estas ações devem ser formatadas para exibição no "Painel de Configurações de IA" para aprovação humana e posterior integração com o sistema "Pomeelli" e módulos de disparo do CRM.

# DIRETRIZES DE ANÁLISE E COMPORTAMENTO
1. **Previsão de Evasão (Churn):** Analise quedas na frequência da catraca, atrasos de pagamento e ausência de agendamentos. Aja preventivamente.
2. **Finanças e Retenção:** Sugira campanhas de upsell (ex: upgrade para plano anual) e recuperação de inativos baseadas no LTV e MRR. Utilize gatilhos mentais fortes.
3. **Marketing e Social Media:** Crie campanhas hiper-segmentadas usando gatilhos de escassez ("vagas limitadas") e comunidade.
4. **Tom de Voz da Marca:** Enérgico, acolhedor, curto, direto e focado em resultados. Use emojis sistematicamente (💪, 🔥, 🚀, ✅).

# REGRAS DE INTEGRAÇÃO (POMEELLI & CRM)
- As ações diárias geradas devem ser estritamente acionáveis (Aprovar/Rejeitar).
- Para ações de Social Media, você DEVE referenciar um `design_template_id` (ex: "template_promocao_01", "template_motivacional_03") para que o Pomeelli saiba qual arte pré-definida usar.
- Você não gera imagens, apenas o copy (texto), a instrução visual e os metadados estruturados.

# FORMATO DE SAÍDA OBRIGATÓRIO (JSON)
Você deve retornar APENAS um objeto JSON válido, SEM ENVOLVER EM BLOCOS DE MARKDOWN (não use ```json e ```). O primeiro caractere deve ser '{' e o último '}'.
"""

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://academiarocksfit.com.br",
        "X-Title": "Rocks Fit CRM"
    }
    
    payload = {
        "model": "qwen/qwen-plus",
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"Analise estes dados reais e gere o relatório JSON: {json.dumps(dados_contexto)}"}
        ]
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=45)
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            # Limpeza defensiva de markdown
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            data = json.loads(content)
            
            # Persistência atômica
            AnaliseGeralIA.objects.create(
                risco_evasao_percentual=data['analise_geral'].get('risco_evasao_percentual', 0),
                saude_financeira=data['analise_geral'].get('saude_financeira', ""),
                insight_do_dia=data['analise_geral'].get('insight_do_dia', "")
            )
            
            for acao in data.get('acoes_diarias_pendentes', []):
                AcaoIA.objects.create(
                    id_acao=acao.get('id_acao', 'acao_indefinida'),
                    tipo=acao.get('tipo', 'OUTRO'),
                    departamento=acao.get('departamento', 'Geral'),
                    titulo_painel=acao.get('titulo_painel', 'Ação Sugerida'),
                    detalhes_para_aprovacao=acao.get('detalhes_para_aprovacao', ''),
                    payload=acao.get('payload_pomeelli') or acao.get('payload_crm') or {}
                )
            
            return data
        else:
            return {"error": f"Erro na API: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"error": str(e)}
