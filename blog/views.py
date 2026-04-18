from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import models
from datetime import date, timedelta
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit
import json

from blog.models import ContactInfo, Program, Schedule, Trainer, Plan, Aluno, PagamentoHistorico, ControleAcesso
from .services import processar_vencimento_catraca
from .forms import ContactForm

def registrar_venda_no_caixa(valor, descricao, metodo='PIX', origem='SITE'):
    """Helper para registrar vendas automáticas vindas do Site ou App no caixa aberto."""
    from blog.models import CaixaTurno, TransacaoCaixa
    from django.utils import timezone
    
    # Tenta encontrar um caixa aberto hoje. Prioriza caixas abertos.
    caixa = CaixaTurno.objects.filter(status='ABERTO').order_by('-abertura').first()
    
    if not caixa:
        # Se não houver caixa aberto (ex: venda de madrugada), 
        # cria um 'Caixa de Sistema' automático se necessário ou ignora se a política for rígida.
        # Aqui, vamos registrar no último caixa fechado como fallback ou criar um temporário.
        # Para este ERP, vamos apenas registrar se houver um caixa para auditoria real.
        return False

    TransacaoCaixa.objects.create(
        caixa=caixa,
        tipo='ENTRADA',
        valor=valor,
        descricao=descricao,
        metodo=metodo,
        origem=origem
    )
    return True


def home(request):
    from django.utils import timezone
    trainers_list = Trainer.objects.all().order_by('order')
    plans_list = Plan.objects.all().order_by('order')
    
    # Horários de Funcionamento
    days_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    schedules = Schedule.objects.all().select_related('trainer', 'program')
    
    # Reorganizar dias para facilitar no template
    days_data = []
    for d_id, d_name in [
        ('monday', 'Segunda'),
        ('tuesday', 'Terça'),
        ('wednesday', 'Quarta'),
        ('thursday', 'Quinta'),
        ('friday', 'Sexta'),
        ('saturday', 'Sábado'),
        ('sunday', 'Domingo'),
    ]:
        days_data.append({
            'id': d_id,
            'name': d_name,
            'schedules': [s for s in schedules if s.day == d_id]
        })
    
    # Dia atual para o destaque
    today = days_order[timezone.now().weekday()]
    
    programs_list = Program.objects.all().order_by('order')
    
    context = {
        "trainers": trainers_list,
        "plans": plans_list,
        "programs": programs_list,
        "days_data": days_data,
        "today": today,
    }
    return render(request, "base/home.html", context)

def programs(request):
    programs_list = Program.objects.all()
    plans_list = Plan.objects.all().order_by('order')
    return render(request, "programs.html", {"programs": programs_list, "plans": plans_list})

def schedule(request):
    programs = Program.objects.all().order_by('order')
    schedules = Schedule.objects.all()
    context = {
        'programs': programs,
        'schedules': schedules,
    }
    return render(request, "schedule.html", context)

def fake_admin(request):
    import socket
    # Pega o IP do intruso (simulação simples)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    
    return render(request, "base/fake_admin.html", {"ip": ip})

@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def contact(request):
    contact_info = ContactInfo.objects.first()
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            return render(
                request, "contact.html", {"contact_info": contact_info, "success": True}
            )
    else:
        form = ContactForm()
    return render(request, "contact.html", {"contact_info": contact_info, "form": form})

def trainers(request):
    trainers_list = Trainer.objects.all().order_by('order')
    return render(request, "trainers.html", {"trainers": trainers_list})

def about(request):
    return render(request, "about.html")

def tools(request):
    return render(request, "tools.html")


def checkout_view(request, plan_id):
    from django.conf import settings
    from .models import SiteConfiguration
    plan = get_object_or_404(Plan, id=plan_id)
    site_config = SiteConfiguration.objects.first()
    return render(request, "base/checkout.html", {
        "plan": plan,
        "debug": settings.DEBUG,
        "site_config": site_config,
    })

@csrf_exempt
def process_payment_api(request):
    """ API Recebe o form (POST + FILES). Registra aluno e redireciona (WhatsApp ou Ton). """
    if request.method == 'POST':
        try:
            # Para suportar upload de arquivos, usamos request.POST em vez de json.loads
            post_data = request.POST
            files_data = request.FILES
            
            # Create or get Aluno
            aluno, created = Aluno.objects.get_or_create(
                cpf=post_data.get('cpf'),
                defaults={
                    'nome_completo': post_data.get('nome_completo'),
                    'email': post_data.get('email'),
                    'whatsapp': post_data.get('whatsapp'),
                    'data_nascimento': post_data.get('data_nascimento')
                }
            )
            
            plano = get_object_or_404(Plan, id=post_data.get('plan_id'))
            payment_method = post_data.get('payment_method', 'local')
            
            acesso, _ = ControleAcesso.objects.get_or_create(aluno=aluno)
            
            historico = PagamentoHistorico.objects.create(
                aluno=aluno,
                plano=plano,
                status='pendente',
                metodo_pagamento=payment_method
            )
            
            if payment_method == 'infinitepay':
                # Inicialmente bloqueado até confirmar pagamento
                acesso.status_catraca = 'bloqueado'
                acesso.save()
                # Tenta usar o link de pagamento exclusivo do plano configurado no admin. 
                # Se não houver, usa o link fallback padrão da loja.
                if plano.infinitepay_link:
                    payment_url = plano.infinitepay_link
                elif plano.button1_url and 'infinitepay.io' in plano.button1_url:
                    payment_url = plano.button1_url
                elif plano.button2_url and 'infinitepay.io' in plano.button2_url:
                    payment_url = plano.button2_url
                else:
                    INFINITEPAY_TAG = "rocks-fit" 
                    payment_url = f"https://pay.infinitepay.io/{INFINITEPAY_TAG}"
                
                # Salvar registro como pendente
                historico.transacao_id = f"INF-{aluno.cpf}"
                historico.save()
                
                return JsonResponse({'success': True, 'action': 'redirect', 'url': payment_url})

            if payment_method == 'local':
                import urllib.parse
                whatsapp_number = "5584999470586" # Fallback oficial Rocks-Fit
                contact = ContactInfo.objects.first()
                if contact and contact.phone:
                    num = ''.join(filter(str.isdigit, contact.phone))
                    if not num.startswith('55'): 
                        num = "55" + num
                    whatsapp_number = num

                # Status: Aguardando Pix manual
                acesso.status_catraca = 'aguardando_pagamento'
                acesso.plano_pendente = plano
                acesso.save()

                msg = f"Olá! Acabei de me cadastrar (Matrícula: {aluno.matricula}). Meu nome é {aluno.nome_completo}. Vou pagar o plano *{plano.name}* via PIX e em seguida enviarei o comprovante aqui."
                wpp_url = f"https://wa.me/{whatsapp_number}?text={urllib.parse.quote(msg)}"
                return JsonResponse({'success': True, 'action': 'redirect', 'url': wpp_url})
            
            return JsonResponse({'success': False, 'error': 'Método de pagamento inválido.'}, status=400)
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Invalid request method'}, status=405)


from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def dev_simular_pagamento(request):
    """APENAS EM DEBUG: Simula pagamento aprovado sem cobrar nada."""
    from django.conf import settings
    if not settings.DEBUG:
        return JsonResponse({'success': False, 'error': 'Apenas em DEBUG.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requerido.'}, status=405)
    try:
        cpf_raw  = request.POST.get('cpf', '')
        nome     = request.POST.get('nome_completo', '')
        email    = request.POST.get('email', 'dev@test.com')
        whatsapp = request.POST.get('whatsapp', '00000000000')
        plan_id  = request.POST.get('plan_id')

        if not cpf_raw or not nome or not plan_id:
            return JsonResponse({'success': False, 'error': 'CPF, Nome e Plano são obrigatórios.'}, status=400)

        cpf_limpo = ''.join(filter(str.isdigit, cpf_raw))
        plano = get_object_or_404(Plan, id=plan_id)

        aluno, _ = Aluno.objects.get_or_create(
            cpf=cpf_limpo,
            defaults={
                'nome_completo': nome, 
                'email': email, 
                'whatsapp': whatsapp,
                'data_nascimento': request.POST.get('data_nascimento', '1990-01-01')
            }
        )

        PagamentoHistorico.objects.create(
            aluno=aluno, plano=plano, status='pago',
            metodo_pagamento='dev_simulate',
            transacao_id='DEV-SIM-' + cpf_limpo,
            valor=plano.price
        )
        
        # Integrar ao Caixa
        registrar_venda_no_caixa(
            valor=plano.price, 
            descricao=f"Matrícula: {aluno.nome_completo} ({plano.name})",
            metodo='PIX', 
            origem='SITE'
        )

        acesso, _ = ControleAcesso.objects.get_or_create(aluno=aluno)
        acesso.status_catraca = 'aguardando_biometria'
        acesso.plano_pendente = plano
        acesso.abrir_catraca_agora = False
        acesso.save()

        return JsonResponse({
            'success': True,
            'message': f'Aluno "{aluno.nome_completo}" cadastrado! Aguardando 1ª entrada biométrica.',
            'status': 'aguardando_biometria',
            'matricula': aluno.matricula,
            'plano': plano.name
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def infinitepay_webhook(request):
    """Recebe notificações de pagamento da InfinityPay"""
    if request.method != 'POST':
        return JsonResponse({'status': 'ignored'})
    try:
        payload = json.loads(request.body)
        event_status = payload.get('status') or payload.get('event', '')
        order_nsu = payload.get('order_nsu', '')

        is_approved = (
            event_status == 'approved' or
            'approved' in str(event_status).lower() or
            'paid' in str(event_status).lower()
        )

        if is_approved and order_nsu:
            cpf_limpo = ''.join(filter(str.isdigit, str(order_nsu)))
            aluno = (Aluno.objects.filter(cpf=cpf_limpo).first() or
                     Aluno.objects.filter(cpf__contains=cpf_limpo).first())

            if not aluno:
                return JsonResponse({'status': 'error', 'message': f'Aluno CPF {order_nsu} nao encontrado.'}, status=404)

            historico = PagamentoHistorico.objects.filter(aluno=aluno, status='pendente').last()
            if historico:
                historico.status = 'pago'
                historico.transacao_id = str(payload.get('id', ''))
                historico.valor = historico.plano.price if historico.plano else 0
                historico.save()

                # Integrar ao Caixa
                registrar_venda_no_caixa(
                    valor=historico.valor,
                    descricao=f"Pagamento InfinitePay: {aluno.nome_completo}",
                    metodo='CREDITO',
                    origem='APP'
                )

            acesso, _ = ControleAcesso.objects.get_or_create(aluno=aluno)
            plano = historico.plano if historico and historico.plano else None
            acesso.status_catraca = 'aguardando_biometria'
            acesso.plano_pendente = plano
            acesso.abrir_catraca_agora = False
            acesso.save()

            return JsonResponse({'status': 'success', 'message': 'Pagamento confirmado. Aguardando biometria.'})

        return JsonResponse({'status': 'ignored', 'event': str(event_status)})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def catraca_sync_api(request):
    """
    Endpoint para o script local baixar a lista de todos os alunos ativos e suas validades.
    """
    from django.conf import settings
    token = request.GET.get('token')
    if token != getattr(settings, 'CATRACA_SYNC_TOKEN', None):
        return JsonResponse({'status': 'error', 'message': 'Não autorizado'}, status=401)

    import datetime
    hoje = datetime.date.today()
    
    # Pegar todos os acessos que não estão vencidos
    acessos = ControleAcesso.objects.filter(data_vencimento__gte=hoje).select_related('aluno')
    
    lista = []
    for acc in acessos:
        lista.append({
            'nome': acc.aluno.nome_completo,
            'cpf': ''.join(filter(str.isdigit, acc.aluno.cpf)),
            'vencimento': acc.data_vencimento.strftime('%Y-%m-%d'),
            'matricula': acc.aluno.matricula
        })
    
    return JsonResponse({'alunos': lista})

def catraca_check_api(request, id_tag):
    """
    Endpoint usado pela Ponte Local para validar um aluno específico (via Matrícula/TAG).
    Retorna foto, nome e dias restantes para o monitor.
    """
    from django.conf import settings
    token = request.GET.get('token')
    if token != getattr(settings, 'CATRACA_SYNC_TOKEN', None):
        return JsonResponse({'status': 'error', 'message': 'Não autorizado'}, status=401)

    # Buscar aluno pela tag/matricula/digital/CPF
    aluno = (Aluno.objects.filter(matricula=id_tag).first() or
             Aluno.objects.filter(digital__icontains=id_tag).first() or
             Aluno.objects.filter(cpf__contains=id_tag).first())

    if not aluno:
        return JsonResponse({'status': 'nao_encontrado', 'nome': 'Desconhecido', 'status_borda': 'vermelho'}, status=404)

    acesso = getattr(aluno, 'acesso', None)
    import datetime
    hoje = datetime.date.today()
    foto_url = request.build_absolute_uri(aluno.foto.url) if aluno.foto else ""

    # 1. AGUARDANDO BIOMETRIA: 1a entrada apos pagamento
    if acesso and acesso.status_catraca == 'aguardando_biometria':
        plano = acesso.plano_pendente
        dias = 30
        if plano:
            mapa = {'diaria': 1, 'mensal': 30, 'trimestral': 90}
            dias = mapa.get(plano.plan_type, getattr(plano, 'duration_days', 30))
        acesso.data_vencimento = hoje + datetime.timedelta(days=dias)
        acesso.status_catraca = 'liberado'
        acesso.plano_pendente = None
        acesso.save()
        return JsonResponse({
            'nome': aluno.nome_completo, 'matricula': aluno.matricula,
            'vencimento': acesso.data_vencimento.strftime('%d/%m/%Y'),
            'dias_restantes': dias, 'foto_url': foto_url,
            'status': 'ativo', 'status_borda': 'verde',
            'mensagem': f'Bem-vindo! Acesso ativado por {dias} dias.'
        })

    # 2. SEM ACESSO
    if not acesso or not acesso.data_vencimento:
        return JsonResponse({
            'status': 'bloqueado', 'nome': aluno.nome_completo,
            'foto_url': foto_url, 'status_borda': 'vermelho',
            'mensagem': 'Sem plano ativo. Procure a recepção.'
        }, status=403)

    dias_restantes = (acesso.data_vencimento - hoje).days

    # 3. VENCIDO
    if dias_restantes < 0:
        acesso.status_catraca = 'bloqueado'
        acesso.save()
        return JsonResponse({
            'nome': aluno.nome_completo, 'matricula': aluno.matricula,
            'vencimento': acesso.data_vencimento.strftime('%d/%m/%Y'),
            'dias_restantes': dias_restantes, 'foto_url': foto_url,
            'status': 'vencido', 'status_borda': 'vermelho',
            'mensagem': 'Plano vencido. Procure a recepção.'
        })

    # 4. ATIVO
    return JsonResponse({
        'nome': aluno.nome_completo, 'matricula': aluno.matricula,
        'vencimento': acesso.data_vencimento.strftime('%d/%m/%Y'),
        'dias_restantes': dias_restantes, 'foto_url': foto_url,
        'status': 'alerta' if dias_restantes <= 5 else 'ativo',
        'status_borda': 'verde',
        'mensagem': f'{dias_restantes} dias restantes.'
    })

def catraca_polling_api(request):
    """
    Mantido para abertura manual via Admin se necessário.
    """
    from django.conf import settings
    token = request.GET.get('token')
    if token != getattr(settings, 'CATRACA_SYNC_TOKEN', None):
        return JsonResponse({'status': 'error', 'message': 'Não autorizado'}, status=401)

    pendentes = ControleAcesso.objects.filter(abrir_catraca_agora=True).select_related('aluno')
    
    data = []
    for acesso in pendentes:
        data.append({
            'aluno_id': acesso.aluno.id,
            'nome': acesso.aluno.nome_completo,
            'cpf': acesso.aluno.cpf,
            'matricula': acesso.aluno.matricula
        })
        acesso.abrir_catraca_agora = False 
        acesso.save()

    return JsonResponse({'liberacoes': data})

@csrf_exempt
def aluno_list_full_api(request):
    """ Retorna todos os alunos para gestão na recepção """
    from django.conf import settings
    token = request.GET.get('token')
    if token != getattr(settings, 'CATRACA_SYNC_TOKEN', None):
        return JsonResponse({'status': 'error', 'message': 'Não autorizado'}, status=401)
    
    import datetime
    hoje = datetime.date.today()
    
    alunos = Aluno.objects.all().select_related('acesso').order_by('-data_cadastro')
    data = []
    for a in alunos:
        status_pagamento = "INATIVO"
        vencimento = "SEM PLANO"
        borda_cor = "vermelho"
        status_catraca = "bloqueado"

        if hasattr(a, 'acesso'):
            ac = a.acesso
            status_catraca = ac.status_catraca

            if ac.status_catraca == 'aguardando_biometria':
                status_pagamento = "PAGO (Aguard. Biometria)"
                borda_cor = "laranja"
                vencimento = "Ativação na 1ª entrada"
            elif ac.status_catraca == 'aguardando_pagamento':
                status_pagamento = "AGUARDANDO PIX (WhatsApp)"
                borda_cor = "amarelo"
                vencimento = "Pendente"
            elif ac.data_vencimento:
                vencimento = ac.data_vencimento.strftime('%d/%m/%Y')
                if ac.data_vencimento >= hoje:
                    status_pagamento = "ATIVO"
                    borda_cor = "verde"
                else:
                    status_pagamento = "INATIVO (VENCIDO)"
                    borda_cor = "vermelho"
            else:
                 status_pagamento = "BLOQUEADO (Não Pago)"
                 borda_cor = "vermelho"

        foto_url = request.build_absolute_uri(a.foto.url) if a.foto else None

        data.append({
            'id': a.id,
            'nome': a.nome_completo,
            'matricula': a.matricula or f"RF{a.id:04d}",
            'cpf': a.cpf,
            'status': status_pagamento,
            'status_catraca': status_catraca,
            'borda_cor': borda_cor,
            'vencimento': vencimento,
            'foto_url': foto_url,
            'tem_foto': bool(a.foto),
            'tem_digital': bool(a.digital)
        })
    return JsonResponse({'alunos': data})

@csrf_exempt
def aluno_update_data_api(request):
    """ Atualiza foto ou biometria de um aluno """
    from django.conf import settings
    token = request.POST.get('token')
    if token != getattr(settings, 'CATRACA_SYNC_TOKEN', None):
        return JsonResponse({'status': 'error', 'message': 'Não autorizado'}, status=401)
    
    if request.method == 'POST':
        aluno_id = request.POST.get('aluno_id')
        aluno = get_object_or_404(Aluno, id=aluno_id)
        
        # Atualizar Foto (Base64)
        foto_b64 = request.POST.get('foto')
        if foto_b64:
            import base64
            from django.core.files.base import ContentFile
            try:
                format, imgstr = foto_b64.split(';base64,')
                ext = format.split('/')[-1]
                img_data = ContentFile(base64.b64decode(imgstr), name=f"aluno_{aluno.matricula}.{ext}")
                aluno.foto = img_data
            except:
                return JsonResponse({'status': 'error', 'message': 'Formato de imagem inválido'}, status=400)
        
        # Atualizar Digital/TAG
        digital = request.POST.get('digital')
        if digital:
            aluno.digital = digital
        
        aluno.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': 'Método inválido'}, status=405)

@csrf_exempt
def whatsapp_webhook(request):
    """Endpoint 'buraco negro' para silenciar as insistentes requisições de webhook do WhatsApp que geram erro 400."""
    return JsonResponse({'status': 'ok'})

@login_required
def crm_dashboard(request):
    """Dashboard com Inteligência Artificial, Demografia e Plano de Ação"""
    alunos = Aluno.objects.all()
    total_alunos = alunos.count()
    hoje = date.today()
    proximos_7_dias = hoje + timedelta(days=7)
    
    ativos = Aluno.objects.filter(acesso__data_vencimento__gte=hoje).count()
    inativos = total_alunos - ativos
    
    # 1. Análise Demográfica (Inspirado no request do usuário)
    # Gênero
    mulheres = alunos.filter(sexo='F').count()
    homens = alunos.filter(sexo='M').count()
    
    # Idade Média
    idades = []
    for a in alunos:
        if a.data_nascimento:
            idade = hoje.year - a.data_nascimento.year - ((hoje.month, hoje.day) < (a.data_nascimento.month, a.data_nascimento.day))
            idades.append(idade)
    
    idade_media = sum(idades) / len(idades) if idades else 0
    
    # 2. Geração de Ações Estratégicas (Relatório Automatizado)
    acoes_gestor = []
    if total_alunos > 0:
        if churn_rate := (inativos / total_alunos * 100) > 15:
            acoes_gestor.append({"titulo": "Reduzir Evasão", "msg": "Ofertar 10% de desconto para renovações feitas hoje."})
        
        if mulheres > homens:
            acoes_gestor.append({"titulo": "Marketing Feminino", "msg": "Criar campanha de modalidade focada no público feminino (ex: Dance/Pilates)."})
        
        if idade_media > 40:
             acoes_gestor.append({"titulo": "Saúde Senior", "msg": "Implementar horários de treinamento focado em mobilidade."})
        else:
             acoes_gestor.append({"titulo": "Performance Jovem", "msg": "Lançar desafios e rankings de força no Instagram."})
    
    # Alertas
    aniversariantes = Aluno.objects.filter(data_nascimento__month=hoje.month, data_nascimento__day=hoje.day)
    vencimentos_proximos = Aluno.objects.filter(acesso__data_vencimento__range=[hoje, proximos_7_dias])
    
    # Insights curtos para o painel principal
    taxa_churn = (inativos / total_alunos * 100) if total_alunos > 0 else 0
    ai_insights = "Análise concluída. Clique no botão de Auditoria para ver o Plano de Ação."

    context = {
        'total_alunos': total_alunos,
        'ativos': ativos,
        'inativos': inativos,
        'aniversariantes': aniversariantes,
        'vencimentos_proximos': vencimentos_proximos,
        'ai_insights': ai_insights,
        'churn_rate': round(taxa_churn, 1),
        'idade_media': round(idade_media, 1),
        'perfil_mulheres': mulheres,
        'perfil_homens': homens,
        'acoes_gestor': acoes_gestor,
        'user_role': getattr(request.user, 'role', 'ALUNO'),
    }
    return render(request, 'crm/dashboard.html', context)

@login_required
def crm_alunos_list(request):
    """Lista de Alunos com Busca por Nome, CPF e Telefone"""
    if not request.user.has_perm('blog.can_manage_students') and not request.user.is_superuser:
        messages.error(request, "Acesso Negado: Sua conta não permite gerenciar a lista de alunos.")
        # Redireciona para o dashboard com a mensagem de erro
        from django.contrib import messages
        return redirect('crm_dashboard')
    query = request.GET.get('q', '')
    if query:
        # Busca tripla: Nome, CPF ou WhatsApp
        alunos = Aluno.objects.filter(
            models.Q(nome_completo__icontains=query) | 
            models.Q(cpf__icontains=query) | 
            models.Q(whatsapp__icontains=query) |
            models.Q(matricula__icontains=query)
        ).distinct()
    else:
        alunos = Aluno.objects.all().order_by('-data_cadastro')
    
    context = {
        'alunos': alunos,
        'query': query
    }
    return render(request, 'crm/alunos_list.html', context)

@login_required
def crm_aluno_detail(request, aluno_id):
    """Gestão Individual do Aluno (Financeiro, Treinos, Pontuação)"""
    if not request.user.has_perm('blog.can_manage_students') and not request.user.is_superuser:
        messages.error(request, "Acesso Negado: Sua conta não permite visualizar detalhes de alunos.")
        return redirect('crm_dashboard')
    from blog.models import Aluno, PagamentoHistorico, Plan
    from django.utils import timezone
    from django.contrib import messages
    
    aluno = get_object_or_404(Aluno, id=aluno_id)
    
    if request.method == 'POST' and 'foto' in request.FILES:
        aluno.foto = request.FILES['foto']
        aluno.save()
        messages.success(request, "Foto do perfil atualizada!")
        return redirect('crm_aluno_detail', aluno_id=aluno.id)

    if request.method == 'POST' and 'faturar' in request.POST:
        valor = request.POST.get('valor')
        metodo = request.POST.get('metodo')
        plano_id = request.POST.get('plano')
        
        # 1. Registrar no Histórico do Aluno
        pagamento = PagamentoHistorico.objects.create(
            aluno=aluno,
            plano_id=plano_id if plano_id else None,
            valor=valor,
            status='pago',
            data_pagamento=timezone.now(),
            metodo_pagamento=metodo
        )
        
        # 2. Atualizar Controle de Acesso Automaticamente
        if plano_id:
            from datetime import date, timedelta
            plano = Plan.objects.get(id=plano_id)
            dias = plano.duration_days
            
            # Se não existe registro de acesso, cria um
            from blog.models import ControleAcesso
            acesso, created = ControleAcesso.objects.get_or_create(aluno=aluno)
            
            # Se o aluno já tem um vencimento futuro, soma os dias a partir de lá. 
            # Se já venceu ou é novo, soma a partir de hoje.
            base_data = acesso.data_vencimento if (acesso.data_vencimento and acesso.data_vencimento > date.today()) else date.today()
            acesso.data_vencimento = base_data + timedelta(days=dias)
            acesso.status_catraca = 'liberado'
            acesso.save()
            messages.success(request, f"Acesso LIBERADO até {acesso.data_vencimento.strftime('%d/%m/%Y')}.")

        # 3. Registrar no Caixa (se houver turno aberto)
        registrar_venda_no_caixa(
            valor=float(valor),
            descricao=f"Pagamento: {aluno.nome_completo} ({plano.name if plano_id else 'Taxa'})",
            metodo=metodo,
            origem='MANUAL'
        )
        
        messages.success(request, f"Pagamento de R$ {valor} processado e enviado ao caixa.")
        return redirect('crm_aluno_detail', aluno_id=aluno.id)

    if request.method == 'POST' and 'liberar_agora' in request.POST:
        if hasattr(aluno, 'acesso'):
            aluno.acesso.abrir_catraca_agora = True
            aluno.acesso.save()
            messages.success(request, f"Comando enviado! A catraca será liberada para {aluno.nome_completo}.")
        else:
            messages.error(request, "Este aluno não possui registro de controle de acesso.")
        return redirect('crm_aluno_detail', aluno_id=aluno.id)

    acesso = getattr(aluno, 'acesso', None)
    pagamentos = aluno.pagamentos.all().order_by('-data_pagamento')
    
    total_investido = sum(p.valor for p in pagamentos if p.status == 'pago')
    debitos = sum(p.valor for p in pagamentos if p.status == 'pendente')
    
    rockspoints = int(total_investido)
    credito = 0.00
    planos = Plan.objects.all()
    
    ultimo_pago = pagamentos.filter(status='pago').first()
    
    context = {
        'aluno': aluno,
        'acesso': acesso,
        'pagamentos': pagamentos,
        'total_pago': total_investido,
        'debitos': debitos,
        'rockspoints': rockspoints,
        'credito': credito,
        'planos': planos,
        'ultimo_pago': ultimo_pago,
    }
    return render(request, 'crm/aluno_detail.html', context)

@login_required
def crm_caixa(request):
    """
    Novo Módulo Financeiro: Caixa Perpétuo Diário.
    """
    if not request.user.has_perm('blog.can_access_financial') and not request.user.is_superuser:
        messages.error(request, "Acesso Restrito: Módulo Financeiro disponível apenas para gestores autorizados.")
        return redirect('crm_dashboard')
    from blog.models import CaixaTurno, TransacaoCaixa, User
    from django.utils import timezone
    from django.db.models import Sum
    from django.contrib import messages
    
    agora = timezone.localtime()
    hoje = agora.date()

    # 🔄 Lógica de Automação: Garantir que o caixa atual seja o do dia de hoje
    # 1. Tenta encontrar qualquer caixa aberto
    caixa_atual = CaixaTurno.objects.filter(status='ABERTO').first()
    
    if caixa_atual and caixa_atual.abertura.date() < hoje:
        # CAIXA ANTIGO DETECTADO! Fechamento automático "Retroativo" (Meia-Noite)
        resumo_velho = caixa_atual.transacoes.aggregate(
            total_in=Sum('valor', filter=models.Q(tipo='ENTRADA')),
            total_out=Sum('valor', filter=models.Q(tipo='SAIDA'))
        )
        total_in = resumo_velho['total_in'] or 0
        total_out = resumo_velho['total_out'] or 0
        
        caixa_atual.saldo_final = caixa_atual.saldo_inicial + total_in - total_out
        caixa_atual.status = 'FECHADO'
        caixa_atual.is_automatico = True
        # Fecha no último segundo do dia em que foi aberto
        caixa_atual.fechamento = timezone.make_aware(
            timezone.datetime.combine(caixa_atual.abertura.date(), timezone.datetime.max.time())
        )
        caixa_atual.save()
        
        # Cria o novo para HOJE começando com o saldo de ontem
        caixa_atual = CaixaTurno.objects.create(
            operador=request.user,
            saldo_inicial=caixa_atual.saldo_final,
            status='ABERTO',
            is_automatico=True
        )
        messages.info(request, "Ciclo diário resetado. Saldo acumulado de ontem transportado.")

    elif not caixa_atual:
        # NENHUM CAIXA ABERTO: Abertura automática de emergência
        ultimo_fechado = CaixaTurno.objects.filter(status='FECHADO').order_by('-fechamento').first()
        saldo_inicial = ultimo_fechado.saldo_final if ultimo_fechado else 0
        
        caixa_atual = CaixaTurno.objects.create(
            operador=request.user,
            saldo_inicial=saldo_inicial,
            status='ABERTO',
            is_automatico=True
        )
        messages.success(request, f"Caixa diário iniciado. Saldo inicial: R$ {saldo_inicial}")

    # 2. Processar Lançamentos Manuais e Estornos (POST)
    if request.method == 'POST':
        acao = request.POST.get('acao')
        
        if acao == 'transacao' and caixa_atual:
            try:
                TransacaoCaixa.objects.create(
                    caixa=caixa_atual,
                    tipo=request.POST.get('tipo'),
                    valor=request.POST.get('valor'),
                    descricao=request.POST.get('descricao'),
                    metodo=request.POST.get('metodo', 'DINHEIRO'),
                    origem='MANUAL'
                )
                messages.success(request, "Operação financeira registrada com sucesso.")
            except Exception as e:
                messages.error(request, f"Erro ao registrar: {e}")
            return redirect('crm_caixa')

        if acao == 'estorno' and caixa_atual:
            try:
                tx_id = request.POST.get('transacao_id')
                tx = TransacaoCaixa.objects.get(id=tx_id, status='NORMAL')
                tx.status = 'ESTORNADO'
                tx.save()
                messages.warning(request, f"Estorno da transação #{tx_id} realizado com sucesso.")
            except Exception as e:
                messages.error(request, f"Erro ao estornar: {e}")
            return redirect('crm_caixa')

        if acao == 'fechar_manual' and caixa_atual:
            # Fechamento manual antecipado se o gestor desejar (Apenas Ativas)
            resumo_calc = caixa_atual.transacoes.filter(status='NORMAL').aggregate(
                total_in=Sum('valor', filter=models.Q(tipo='ENTRADA')),
                total_out=Sum('valor', filter=models.Q(tipo='SAIDA'))
            )
            tin = resumo_calc['total_in'] or 0
            tout = resumo_calc['total_out'] or 0
            caixa_atual.saldo_final = caixa_atual.saldo_inicial + tin - tout
            caixa_atual.status = 'FECHADO'
            caixa_atual.fechamento = timezone.now()
            caixa_atual.save()
            messages.warning(request, "Caixa encerrado manualmente antes do ciclo automático.")
            return redirect('crm_caixa')

    # 3. Dados do Dashboard (Filtrando as ATIVAS)
    transacoes = caixa_atual.transacoes.all().order_by('-data_hora')
    resumo = {'dinheiro': 0, 'pix': 0, 'cartao': 0, 'saidas': 0, 'total': 0, 'volume_h': []}
    
    for t in [tx for tx in transacoes if tx.status == 'NORMAL']:
        if t.tipo == 'ENTRADA':
            if t.metodo == 'DINHEIRO': resumo['dinheiro'] += t.valor
            elif t.metodo == 'PIX': resumo['pix'] += t.valor
            else: resumo['cartao'] += t.valor
            resumo['total'] += t.valor
        else:
            resumo['saidas'] += t.valor
            resumo['total'] -= t.valor

    # Histórico de fechamentos
    historico_caixas = CaixaTurno.objects.filter(status='FECHADO').order_by('-fechamento')[:15]

    context = {
        'caixa': caixa_atual,
        'transacoes': transacoes,
        'resumo': resumo,
        'historico_caixas': historico_caixas,
    }
    return render(request, 'crm/caixa.html', context)
