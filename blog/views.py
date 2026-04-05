from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit
import json

from blog.models import ContactInfo, Program, Schedule, Trainer, Plan, Aluno, PagamentoHistorico, ControleAcesso
from .services import processar_vencimento_catraca
from .forms import ContactForm

def home(request):
    from django.utils import timezone
    trainers_list = Trainer.objects.all()
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
    trainers_list = Trainer.objects.all()
    return render(request, "trainers.html", {"trainers": trainers_list})

def about(request):
    return render(request, "about.html")

def tools(request):
    return render(request, "tools.html")


def checkout_view(request, plan_id):
    from django.conf import settings
    plan = get_object_or_404(Plan, id=plan_id)
    return render(request, "base/checkout.html", {
        "plan": plan,
        "debug": settings.DEBUG
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
                # Link direto para a plataforma InfinityPay da loja
                # Formato: https://pay.infinitepay.io/TAG_DA_LOJA
                INFINITEPAY_TAG = "rocks-fit" 
                
                # Opcional: Adicionar o valor ao link se a InfinityPay suportar no formato de query param
                # ou apenas redirecionar para a página principal da loja na InfinityPay
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

                msg = f"Olá! Acabei de me cadastrar (Matrícula: {aluno.matricula}). Meu nome é {aluno.nome_completo} e quero pagar o plano *{plano.name}* via PIX. Por favor, me envie a *Chave PIX* da academia."
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
            transacao_id='DEV-SIM-' + cpf_limpo
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
                historico.save()

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
    """
    Recebe notificações e mensagens do WhatsApp (Meta Cloud API).
    GET: Verificação inicial (Hub Challenge).
    POST: Eventos de mensagem, leitura, etc.
    """
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        
        # O TOKEN_VERIFICACAO abaixo deve ser o mesmo configurado no Painel do Desenvolvedor da Meta
        VERIFY_TOKEN = "rocks_fit_verification" 
        
        if mode == "subscribe" and token == VERIFY_TOKEN:
            from django.http import HttpResponse
            return HttpResponse(challenge)
        return HttpResponse("Erro de Verificação", status=403)

    if request.method == "POST":
        try:
            payload = json.loads(request.body)
            # Aqui você pode processar a mensagem se quiser automatizar algo futuramente.
            # Por enquanto, apenas retornamos 200 para parar o erro 404.
            print(f"--- Recebido Webhook WhatsApp: {payload}")
            return JsonResponse({"status": "received"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"error": "Method not allowed"}, status=405)
