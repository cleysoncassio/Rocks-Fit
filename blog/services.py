from datetime import timedelta
from django.utils import timezone
from .models import ControleAcesso

def processar_vencimento_catraca(aluno, plano):
    """
    Atualiza o tempo de catraca do usuário baseado no plano pago.
    Utiliza as regras de negócio: diária (+1 dia), mensal (+30 dias), trimestral (+90 dias)
    Para o fluxo Híbrido Ton/WhatsApp, isso pode ser chamado manualmente no Admin
    ou após o Webhook, caso exista. Por padrão, geramos 'liberado'.
    """
    acesso, created = ControleAcesso.objects.get_or_create(aluno=aluno)

    hoje = timezone.now().date()
    
    # Se já tem um plano ativo e no futuro, adiciona os dias sobre o vencimento existente.
    # Caso contrário, baseia no dia de hoje.
    if acesso.data_vencimento and acesso.data_vencimento > hoje:
        base_date = acesso.data_vencimento
    else:
        base_date = hoje

    if plano.plan_type == 'diaria':
        acesso.data_vencimento = base_date + timedelta(days=1)
    elif plano.plan_type == 'trimestral':
        acesso.data_vencimento = base_date + timedelta(days=90)
    else: # mensal
        acesso.data_vencimento = base_date + timedelta(days=30)
    
    acesso.status_catraca = 'liberado'
    acesso.save()
    return acesso
