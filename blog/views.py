from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import models
from datetime import date, timedelta
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit
import json

from blog.models import ContactInfo, Program, Schedule, Trainer, Plan, Aluno, PagamentoHistorico, ControleAcesso
from django.utils import timezone
from .services import processar_vencimento_catraca
from .forms import ContactForm

def registrar_venda_no_caixa(valor, descricao, metodo='PIX', origem='SITE'):
    """Helper para registrar vendas automáticas vindas do Site ou App no caixa aberto."""
    from blog.models import CaixaTurno, TransacaoCaixa
    
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


def crm_reparar_banco(request):
    """NUCLEAR OPTION: Executa GRANT via Python para tentar destravar o banco na Hostman"""
    from django.db import connection
    results = []
    commands = [
        "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO Rocksfit;",
        "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO Rocksfit;",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO Rocksfit;"
    ]
    
    try:
        with connection.cursor() as cursor:
            for cmd in commands:
                try:
                    cursor.execute(cmd)
                    results.append(f"✅ SUCESSO: {cmd}")
                except Exception as e:
                    results.append(f"❌ FALHA: {cmd} | Erro: {e}")
        
        return HttpResponse("<h2>Resultado do Reparo:</h2>" + "<br>".join(results) + "<br><br><a href='/'>Voltar para Home</a>")
    except Exception as e:
        return HttpResponse(f"ERRO CRÍTICO NO REPARADOR: {e}")


def home(request):
    # Inicializa variáveis com valores vazios caso o banco negue acesso (InsufficientPrivilege)
    trainers_list = []
    plans_list = []
    programs_list = []
    days_data = []
    today = "monday"
    
    try:
        from django.utils import timezone
        # Consultas defensivas para evitar Erro 500 se as migrações ou permissões falharem no Hostman
        try:
            trainers_list = list(Trainer.objects.all().order_by('order'))
            plans_list = list(Plan.objects.all().order_by('order'))
            programs_list = list(Program.objects.all().order_by('order'))
        except Exception as e:
            print(f"[DB_ERROR] Erro ao carregar ordenação: {e}")
            trainers_list = list(Trainer.objects.all().order_by('id'))
            plans_list = list(Plan.objects.all().order_by('id'))
            programs_list = list(Program.objects.all().order_by('id'))

        # Horários de Funcionamento (Envolvido em try específico pois a tabela schedule está com erro de permissão)
        try:
            days_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            # O Segredo: Transformar em list() IMEDIATAMENTE para capturar o erro aqui e não depois
            schedules_qs = Schedule.objects.all().select_related('trainer', 'program')
            schedules = list(schedules_qs) 
            
            for d_id, d_name in [
                ('monday', 'Segunda'), ('tuesday', 'Terça'), ('wednesday', 'Quarta'),
                ('thursday', 'Quinta'), ('friday', 'Sexta'), ('saturday', 'Sábado'), ('sunday', 'Domingo'),
            ]:
                days_data.append({
                    'id': d_id,
                    'name': d_name,
                    'schedules': [s for s in schedules if s.day == d_id]
                })
            today = days_order[timezone.now().weekday()]
        except Exception as e:
            print(f"[DB_ERROR] Erro ao carregar horários (Schedule): {e}")
            days_data = []

        context = {
            "trainers": trainers_list,
            "plans": plans_list,
            "programs": programs_list,
            "days_data": days_data,
            "today": today,
        }
        return render(request, "base/home.html", context)
    except Exception as e:
        import traceback
        return HttpResponse(f"ERRO DE DIAGNÓSTICO ROCKS-FIT (HOME): {str(e)}<br><pre>{traceback.format_exc()}</pre>", status=500)
    except Exception as e:
        import traceback
        return HttpResponse(f"ERRO DE DIAGNÓSTICO ROCKS-FIT (HOME): {str(e)}<br><pre>{traceback.format_exc()}</pre>", status=500)

def programs(request):
    programs_list = Program.objects.all()
    try:
        plans_list = Plan.objects.all().order_by('order')
    except:
        plans_list = Plan.objects.all().order_by('id')
    return render(request, "programs.html", {"programs": programs_list, "plans": plans_list})

def schedule(request):
    try:
        programs = Program.objects.all().order_by('order')
    except:
        programs = Program.objects.all().order_by('id')
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
                    'data_nascimento': post_data.get('data_nascimento'),
                    'status': 'AGUARDANDO'
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
                'data_nascimento': request.POST.get('data_nascimento', '1990-01-01'),
                'status': 'AGUARDANDO'
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

        # Ativação Automática do Status de Gestão
        aluno.status = 'ATIVO'
        aluno.save()

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

                # Ativação Automática do Aluno
                aluno.status = 'ATIVO'
                aluno.save()

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

    # 4. LÓGICA DE ENTRADA/SAÍDA (ESGOTAMENTO POR USO)
    # Alternar estado (Se estava fora, entra. Se estava dentro, sai).
    esta_saindo = acesso.esta_dentro
    acesso.esta_dentro = not acesso.esta_dentro
    acesso.ultimo_acesso = timezone.now()
    
    msg_complemento = "Entrada confirmada."
    if esta_saindo:
        msg_complemento = "Saída confirmada. Bom descanso!"
        # Se for DIÁRIA, esgota o acesso após a saída
        # Verificamos pelo nome do plano ou tipo
        ultimo_pago = aluno.pagamentos.filter(status='pago', plano__isnull=False).order_by('-data_pagamento').first()
        if ultimo_pago and ultimo_pago.plano.plan_type == 'diaria':
            acesso.data_vencimento = hoje - datetime.timedelta(days=1)
            acesso.status_catraca = 'bloqueado'
            msg_complemento = "Diária esgotada (Ciclo concluído). Até a próxima!"
            
    acesso.save()

    return JsonResponse({
        'nome': aluno.nome_completo, 'matricula': aluno.matricula,
        'vencimento': acesso.data_vencimento.strftime('%d/%m/%Y'),
        'dias_restantes': dias_restantes, 'foto_url': foto_url,
        'status': 'alerta' if dias_restantes <= 5 else 'ativo',
        'status_borda': 'verde',
        'mensagem': f'{msg_complemento}'
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
    
    from django.utils import timezone
    hoje = timezone.now().date()
    
    alunos = Aluno.objects.all().select_related('acesso').order_by('-data_cadastro')
    data = []
    
    for a in alunos:
        try:
            status_pagamento = "INATIVO"
            vencimento = "SEM PLANO"
            borda_cor = "vermelho"
            status_catraca = "bloqueado"

            if hasattr(a, 'acesso'):
                ac = a.acesso
                status_catraca = str(ac.status_catraca)

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

            # Crítico: O Bridge (ponte_rocksfit) precisa de URL ABSOLUTA para carregar imagens
            try:
                foto_url = request.build_absolute_uri(a.foto.url) if a.foto else None
            except:
                foto_url = None

            data.append({
                'id': a.id,
                'nome': str(a.nome_completo or "Sem Nome")[:50],
                'matricula': a.matricula or f"RF{a.id:04d}",
                'cpf': a.cpf or "",
                'status': status_pagamento,
                'status_catraca': status_catraca,
                'borda_cor': borda_cor,
                'vencimento': vencimento,
                'foto_url': foto_url,
                'tem_foto': bool(a.foto),
                'tem_digital': bool(a.digital)
            })
        except:
            continue

    return JsonResponse({'alunos': data, 'total': len(data)})

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
    """Dashboard com Inteligência Artificial, Demografia e Plano de Ação (Super Defensivo)"""
    from blog.models import GymSetting, Aluno, Plan, PagamentoHistorico, ControleAcesso
    from datetime import date, timedelta
    from django.contrib import messages
    from django.utils import timezone
    
    # Safely import the helper function if it exists. Sometimes it's inside views.py
    try:
        from blog.views import registrar_venda_no_caixa
    except ImportError:
        pass

    if request.method == 'POST' and 'faturar_rapido' in request.POST:
        aluno_id = request.POST.get('aluno_id')
        valor_raw = request.POST.get('valor', '0.00').strip()
        metodo = request.POST.get('metodo', 'DINHEIRO')
        plano_id = request.POST.get('plano', '')
        
        if ',' in valor_raw:
            valor = valor_raw.replace('.', '').replace(',', '.')
        else:
            valor = valor_raw
            
        try:
            aluno = Aluno.objects.get(id=aluno_id)
            # 1. Registro Histórico
            PagamentoHistorico.objects.create(
                aluno=aluno,
                plano_id=plano_id if plano_id else None,
                valor=valor,
                status='pago',
                data_pagamento=timezone.now(),
                metodo_pagamento=metodo
            )
            
            # 2. Atualizar Acesso (se tiver plano)
            plano_name = 'Taxa Adicional'
            if plano_id:
                plano = Plan.objects.get(id=plano_id)
                plano_name = plano.name
                acesso, _ = ControleAcesso.objects.get_or_create(aluno=aluno)
                hoje_local = timezone.localtime(timezone.now()).date()
                base_data = hoje_local
                if hoje_local.weekday() == 6: # Domingo
                    base_data = hoje_local + timedelta(days=1)
                    
                if plano.plan_type == 'diaria':
                    acesso.data_vencimento = base_data + timedelta(days=plano.duration_days)
                else:
                    start_date = acesso.data_vencimento if (acesso.data_vencimento and acesso.data_vencimento > hoje_local) else base_data
                    acesso.data_vencimento = start_date + timedelta(days=plano.duration_days)
                
                acesso.status_catraca = 'liberado'
                acesso.esta_dentro = False
                acesso.save()
                
            # 3. Caixa
            if 'registrar_venda_no_caixa' in globals() or 'registrar_venda_no_caixa' in locals():
                registrar_venda_no_caixa(
                    valor=float(valor),
                    descricao=f"Recebimento Rápido: {aluno.nome_completo} ({plano_name})",
                    metodo=metodo,
                    origem='MANUAL'
                )
            messages.success(request, f"Recebimento Rápido: R$ {valor} computado para o membro '{aluno.nome_completo}'.")
        except Exception as e:
            messages.error(request, f"Aconteceu um erro no aporte rápido: {str(e)}")
            
        return redirect('crm_dashboard')

    context = {'ai_insights': 'Acesso limitado ao banco.'}
    try:
        hoje = date.today()
        # Blocos isolados
        try:
            alunos = Aluno.objects.all()
            context['alunos_lista'] = alunos.order_by('nome_completo')
            context['planos'] = Plan.objects.all()
            context['total_alunos'] = alunos.count()
            context['perfil_mulheres'] = alunos.filter(sexo='F').count()
            context['perfil_homens'] = alunos.filter(sexo='M').count()
        except: pass

        try:
            context['ativos'] = Aluno.objects.filter(acesso__data_vencimento__gte=hoje).count()
        except: pass

        from blog.models import GymSetting
        context['gym_settings'] = GymSetting.objects.first()
        context['user_role'] = getattr(request.user, 'role', 'ALUNO')

        return render(request, 'crm/dashboard.html', context)
    except Exception as e:
        return HttpResponse(f"Erro Dashboard: {e}", status=500)

@login_required
def crm_config(request):
    """Gestão de permissões de SEGURANÇA MÁXIMA: Apenas modelos CORE do CRM"""
    if not request.user.is_superuser:
        return HttpResponse("Acesso Negado", status=403)

    from django.contrib.auth.models import Permission
    from .models import RolePermission, User
    
    # 1. WHITELIST: Apenas estes modelos aparecem no CRM
    modelos_autorizados = [
        'user', 'aluno', 'caixaturno', 'caixamovimentacao', 
        'pagamentohistorico', 'plano', 'controleacesso', 
        'nutricionista', 'rolepermission', 'exercicio', 'treino', 'avaliacao'
    ]
    
    # 2. Mapeamento de termos técnicos para Português amigável
    traducoes = {
        'Can add': 'Adicionar',
        'Can change': 'Editar',
        'Can delete': 'Excluir',
        'Can view': 'Visualizar',
        # Modelos
        'user': 'Usuários',
        'aluno': 'Alunos',
        'caixaturno': 'Turno de Caixa',
        'caixamovimentacao': 'Movimento de Caixa',
        'pagamentohistorico': 'Histórico Financeiro',
        'plano': 'Planos e Pacotes',
        'controleacesso': 'Acesso/Catraca',
        'nutricionista': 'Nutrição',
        'rolepermission': 'Cargos e Permissões',
        'treino': 'Treinos',
        'avaliacao': 'Avaliações Fis.',
    }

    target_roles = [User.TYPE_SECRETARY, User.TYPE_TRAINER, User.TYPE_NUTRITIONIST, User.TYPE_STUDENT]
    
    if request.method == 'POST':
        for r_type in target_roles:
            role_perm, _ = RolePermission.objects.get_or_create(role=r_type)
            perm_ids = request.POST.getlist(f'perms_{r_type}')
            role_perm.permissions.set(Permission.objects.filter(id__in=perm_ids))
        return redirect('crm_config')

    # Busca apenas permissões dos modelos autorizados
    all_perms_queryset = Permission.objects.filter(
        content_type__app_label='blog',
        content_type__model__in=modelos_autorizados
    ).order_by('content_type__model', 'codename')
    
    # Prepara nomes amigáveis baseados na tradução técnica e de modelos
    all_perms_friendly = []
    for p in all_perms_queryset:
        modelo_eng = p.content_type.model
        modelo_pt = traducoes.get(modelo_eng, modelo_eng.capitalize())
        
        prefixo_pt = "Ação"
        for eng, pt in traducoes.items():
            if p.name.startswith(eng):
                prefixo_pt = pt
                break
        
        p.friendly_name = f"{prefixo_pt} {modelo_pt}"
        all_perms_friendly.append(p)
    
    role_configs = [RolePermission.objects.get_or_create(role=r)[0] for r in target_roles]

    context = {
        'role_configs': role_configs,
        'all_perms': all_perms_friendly,
        'ai_insights': 'Módulo CRM Blindado - Apenas Operação.',
    }
    return render(request, 'crm/config.html', context)

@login_required
def crm_dash_gerencial(request):
    """Dashboard Gerencial com métricas reais baseadas na importação de dados"""
    from blog.models import GymSetting, Aluno, PagamentoHistorico, ControleAcesso
    from django.db.models import Sum, Avg
    from datetime import date, timedelta
    
    gym_settings = GymSetting.objects.first()
    hoje = date.today()
    
    # 1. Métricas de Volume
    total_alunos = Aluno.objects.count()
    alunos_ativos = Aluno.objects.filter(acesso__data_vencimento__gte=hoje).count()
    inativos = total_alunos - alunos_ativos
    
    # 2. Clientes em Risco (Vencem nos próximos 7 dias ou venceram nos últimos 7)
    janela_risco = hoje + timedelta(days=7)
    janela_passada = hoje - timedelta(days=7)
    clientes_risco = Aluno.objects.filter(
        acesso__data_vencimento__range=[janela_passada, janela_risco]
    ).count()
    
    # 3. Métricas Financeiras Reais (LTV)
    # Somamos todos os PagamentoHistorico importados
    faturamento_total = PagamentoHistorico.objects.filter(status='pago').aggregate(Sum('valor'))['valor__sum'] or 0
    ltv_medio = faturamento_total / total_alunos if total_alunos > 0 else 0
    
    # 4. Taxa de Retenção (Alunos Ativos / Total)
    taxa_retencao = (alunos_ativos / total_alunos * 100) if total_alunos > 0 else 0

    context = {
        'gym_settings': gym_settings,
        'total_alunos': total_alunos,
        'alunos_ativos': alunos_ativos,
        'inativos': inativos,
        'ltv_valor': f"R$ {ltv_medio:,.2f}",
        'churn_evasao': f"{100 - taxa_retencao:.1f}%",
        'clientes_risco': clientes_risco,
        'taxa_renovacao': f"{taxa_retencao:.1f}%",
    }
    return render(request, "crm/dash_gerencial.html", context)

@login_required
def crm_alunos_list(request):
    """Lista de Alunos otimizada com Busca, Filtros e Paginação"""
    try:
        if not request.user.has_perm('blog.can_manage_students') and not request.user.is_superuser:
            messages.error(request, "Acesso Negado.")
            return redirect('crm_dashboard')
        
        query = request.GET.get('q', '')
        status_filter = request.GET.get('status', '').upper()
        
        # 1. Otimização: select_related('acesso') evita 1 query extra por aluno (N+1)
        alunos_list = Aluno.objects.all().select_related('acesso').order_by('-data_cadastro')
        
        if query:
            alunos_list = alunos_list.filter(
                models.Q(nome_completo__icontains=query) | 
                models.Q(cpf__icontains=query) | 
                models.Q(whatsapp__icontains=query) |
                models.Q(matricula__icontains=query)
            ).distinct()
            
        if status_filter in ['ATIVO', 'INATIVO', 'INADIMPLENTE', 'SUSPENSO', 'AGUARDANDO']:
            alunos_list = alunos_list.filter(status=status_filter)
        
        total_count = alunos_list.count()
        
        # 2. Paginação: 50 alunos por página para não travar o navegador
        from django.core.paginator import Paginator
        paginator = Paginator(alunos_list, 50)
        page_number = request.GET.get('page')
        alunos = paginator.get_page(page_number)
        
        # 3. Contadores Totais (Independente da filtragem atual para os botões)
        from django.db.models import Count
        counts = Aluno.objects.values('status').annotate(total=Count('id'))
        status_counts = {item['status']: item['total'] for item in counts}
        
        counts_data = {
            'total': Aluno.objects.count(),
            'ativo': status_counts.get('ATIVO', 0),
            'inativo': status_counts.get('INATIVO', 0),
            'inadimplente': status_counts.get('INADIMPLENTE', 0),
            'aguardando': status_counts.get('AGUARDANDO', 0),
        }
        
        from blog.models import GymSetting
        gym_settings = GymSetting.objects.first()

        context = {
            'alunos': alunos,
            'query': query,
            'status_filter': status_filter,
            'total_count': total_count,
            'counts_data': counts_data,
            'gym_settings': gym_settings,
        }
        return render(request, 'crm/alunos_list.html', context)
    except Exception as e:
        import traceback
        return HttpResponse(f"ERRO DE DIAGNÓSTICO ROCKS-FIT: {str(e)}<br><pre>{traceback.format_exc()}</pre>", status=500)

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
        
        # Se o aluno estava aguardando biometria para ativar o plano, ativa agora!
        from blog.models import ControleAcesso
        acesso, created = ControleAcesso.objects.get_or_create(aluno=aluno)
        
        if acesso.status_catraca == 'aguardando_biometria' and acesso.plano_pendente:
            from datetime import timedelta
            plano = acesso.plano_pendente
            hoje_local = timezone.localtime(timezone.now()).date()
            
            # Regra do Domingo
            base_data = hoje_local
            if hoje_local.weekday() == 6: # Domingo
                base_data = hoje_local + timedelta(days=1)
                
            acesso.data_vencimento = base_data + timedelta(days=plano.duration_days)
            acesso.status_catraca = 'liberado'
            acesso.plano_pendente = None
            acesso.abrir_catraca_agora = True # Abre na hora pós-foto!
            acesso.save()
            messages.success(request, f"Biometria Facial Cadastrada! Plano '{plano.name}' ativado e catraca liberada.")
        else:
            messages.success(request, "Foto do perfil atualizada!")
            
        return redirect('crm_aluno_detail', aluno_id=aluno.id)

    if request.method == 'POST' and 'faturar' in request.POST:
        valor_raw = request.POST.get('valor', '0.00').strip()
        if ',' in valor_raw:
            valor = valor_raw.replace('.', '').replace(',', '.')
        else:
            valor = valor_raw
            
        metodo = request.POST.get('metodo', 'DINHEIRO')
        plano_id = request.POST.get('plano', '')
        
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
            from datetime import timedelta
            plano = Plan.objects.get(id=plano_id)
            dias = plano.duration_days
            
            from blog.models import ControleAcesso
            acesso, created = ControleAcesso.objects.get_or_create(aluno=aluno)
            
            hoje_local = timezone.localtime(timezone.now()).date()
            base_data = hoje_local
            if hoje_local.weekday() == 6: # Domingo
                base_data = hoje_local + timedelta(days=1)

            # Se for DIÁRIA, não acumula (reseta para o prazo do plano)
            if plano.plan_type == 'diaria':
                acesso.data_vencimento = base_data + timedelta(days=dias)
            else:
                # Se for Mensal/etc, acumula se o vencimento for futuro
                start_date = acesso.data_vencimento if (acesso.data_vencimento and acesso.data_vencimento > hoje_local) else base_data
                acesso.data_vencimento = start_date + timedelta(days=dias)

            acesso.status_catraca = 'liberado'
            acesso.esta_dentro = False
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

    if request.method == 'POST' and 'cadastro_digital' in request.POST:
        digital_id = request.POST.get('digital_id')
        aluno.digital = digital_id
        aluno.save()
        messages.success(request, f"Biometria Digital vinculada com sucesso: ID {digital_id}")
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

    # --- AUTO-SYNC: Garantir que o acesso esteja sincronizado com o último pagamento ---
    ultimo_pago = pagamentos.filter(status='pago').first()
    if ultimo_pago and ultimo_pago.plano:
        from blog.models import ControleAcesso
        from datetime import date, timedelta
        ac, created = ControleAcesso.objects.get_or_create(aluno=aluno)
        
        # Se o aluno tem um plano pago mas a catraca está sem data ou vencida, sincroniza
        # --- REGRA DO DOMINGO: Se pagar domingo, começa a contar de segunda ---
        data_local = timezone.localtime(ultimo_pago.data_pagamento).date()
        if data_local.weekday() == 6: # 6 = Domingo
            base_data_calculo = data_local + timedelta(days=1)
        else:
            base_data_calculo = data_local
            
        vencimento_calculado = base_data_calculo + timedelta(days=ultimo_pago.plano.duration_days)
        
        # Se for diária, a gente força o vencimento calculado (sem somar)
        # Se for mensal, a gente só atualiza se estiver vazio ou se o novo cálculo for MAIOR
        if ultimo_pago.plano.plan_type == 'diaria':
            if ac.data_vencimento != vencimento_calculado:
                ac.data_vencimento = vencimento_calculado
                ac.status_catraca = 'liberado'
                ac.save()
                acesso = ac
        else:
            if not ac.data_vencimento or ac.data_vencimento < vencimento_calculado:
                ac.data_vencimento = vencimento_calculado
                ac.status_catraca = 'liberado'
                ac.save()
                acesso = ac
    # -----------------------------------------------------------------------------------

    from blog.models import GymSetting
    gym_settings = GymSetting.objects.first()

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
        'gym_settings': gym_settings,
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
    from blog.models import CaixaTurno, TransacaoCaixa, User, GymSetting
    from django.utils import timezone
    from django.db.models import Sum, Q
    import datetime
    
    agora = timezone.localtime()
    hoje = agora.date()

    # 🔄 Lógica de Automação: Garantir que o caixa atual seja o do dia de hoje
    # 1. Tenta encontrar qualquer caixa aberto
    caixa_atual = CaixaTurno.objects.filter(status='ABERTO').first()
    
    if caixa_atual and caixa_atual.abertura.date() < hoje:
        # CAIXA ANTIGO DETECTADO! Fechamento automático "Retroativo" (Meia-Noite)
        resumo_velho = caixa_atual.transacoes.aggregate(
            total_in=Sum('valor', filter=Q(tipo='ENTRADA')),
            total_out=Sum('valor', filter=Q(tipo='SAIDA'))
        )
        total_in = resumo_velho['total_in'] or 0
        total_out = resumo_velho['total_out'] or 0
        
        caixa_atual.saldo_final = caixa_atual.saldo_inicial + total_in - total_out
        caixa_atual.status = 'FECHADO'
        caixa_atual.is_automatico = True
        # Fecha no último segundo do dia em que foi aberto
        caixa_atual.fechamento = timezone.make_aware(
            datetime.datetime.combine(caixa_atual.abertura.date(), datetime.time.max)
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

        if acao == 'fechar' and caixa_atual:
            # Fechamento manual antecipado se o gestor desejar (Apenas Ativas)
            resumo_calc = caixa_atual.transacoes.filter(status='NORMAL').aggregate(
                total_in=Sum('valor', filter=Q(tipo='ENTRADA')),
                total_out=Sum('valor', filter=Q(tipo='SAIDA'))
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
    from blog.models import GymSetting
    gym_settings = GymSetting.objects.first()
    
    transacoes = caixa_atual.transacoes.all().order_by('-data_hora')
    resumo = {
        'dinheiro': 0, 
        'pix': 0, 
        'cartao': 0, 
        'saidas': 0, 
        'entradas': 0,
        'total': caixa_atual.saldo_inicial, # Começa com o saldo que já estava no caixa
        'volume_h': []
    }
    
    for t in [tx for tx in transacoes if tx.status == 'NORMAL']:
        if t.tipo == 'ENTRADA':
            if t.metodo == 'DINHEIRO': resumo['dinheiro'] += t.valor
            elif t.metodo == 'PIX': resumo['pix'] += t.valor
            else: resumo['cartao'] += t.valor
            resumo['total'] += t.valor
            resumo['entradas'] += t.valor
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
        'gym_settings': gym_settings,
    }
    return render(request, 'crm/caixa.html', context)

@login_required
def crm_aluno_delete(request, aluno_id):
    """
    Exclusão Segura de Perfil de Aluno com travas de segurança rigorosas.
    """
    if not request.user.has_perm('blog.can_manage_students') and not request.user.is_superuser:
        messages.error(request, "Acesso Negado: Permissão insuficiente para exclusão.")
        return redirect('crm_aluno_detail', aluno_id=aluno_id)

    from blog.models import Aluno, ControleAcesso
    from django.shortcuts import get_object_or_404
    
    aluno = get_object_or_404(Aluno, id=aluno_id)
    acesso = ControleAcesso.objects.filter(aluno=aluno).first()
    debitos_pendentes = aluno.pagamentos.filter(status='pendente').count()
    
    from django.utils import timezone
    hoje = timezone.now().date()
    
    # 🕵️ Verificação de Travas Rigorosas
    # 1. Trava de Plano Ativo (Verifica data de vencimento real)
    tem_plano_vigente = acesso and acesso.data_vencimento and acesso.data_vencimento >= hoje
    if tem_plano_vigente:
        messages.error(request, "VETO: Não é possível excluir um aluno com PLANO VIGENTE. Aguarde o vencimento ou cancele o contrato antes de excluir.")
        return redirect('crm_aluno_detail', aluno_id=aluno_id)
        
    # 2. Trava de Inadimplência
    if aluno.status == 'INADIMPLENTE':
        messages.error(request, "VETO FINANCEIRO: Alunos com status de INADIMPLENTE não podem ser removidos até a quitação total dos débitos.")
        return redirect('crm_aluno_detail', aluno_id=aluno_id)
        
    # 3. Trava de Saldo (Opcional por enquanto, já que credito é 0.00)
    # Se no futuro houver saldo real, a trava já estaria aqui.

    # Protocolo de Exclusão
    nome_aluno = aluno.nome_completo
    aluno.delete()
    messages.success(request, f"PROTOCOLO CONCLUÍDO: O perfil de {nome_aluno} foi permanentemente removido.")
    return redirect('crm_alunos_list')

@login_required
def crm_aluno_create(request):
    """Criação de novos alunos com dados completos"""
    if not request.user.has_perm('blog.can_manage_students') and not request.user.is_superuser:
        messages.error(request, "Acesso Negado: Permissão insuficiente.")
        return redirect('crm_alunos_list')
    
    from .models import GymSetting, ControleAcesso, Plan, PagamentoHistorico
    from .forms import AlunoForm
    from django.utils import timezone
    
    gym_settings = GymSetting.objects.first()
    planos = Plan.objects.all()
    
    if request.method == 'POST':
        form = AlunoForm(request.POST, request.FILES)
        if form.is_valid():
            aluno = form.save(commit=False)
            
            # Processar imagem da webcam (Base64) se houver
            webcam_image = request.POST.get('webcam_image')
            if webcam_image and not request.FILES.get('foto'):
                import base64
                from django.core.files.base import ContentFile
                try:
                    format, imgstr = webcam_image.split(';base64,')
                    ext = format.split('/')[-1]
                    data = ContentFile(base64.b64decode(imgstr), name=f"aluno_webcam_{aluno.cpf}.{ext}")
                    aluno.foto = data
                except:
                    pass
            
            aluno.save()
            
            # Criar controle de acesso (sempre)
            acesso, _ = ControleAcesso.objects.get_or_create(aluno=aluno)

            # Lógica de Aporte Inicial (Plano imediato)
            plano_id = request.POST.get('plano_id')
            if plano_id:
                valor_raw = request.POST.get('valor_pagamento', '').strip()
                metodo = request.POST.get('metodo_pagamento', 'PIX')
                plano = Plan.objects.get(id=plano_id)
                
                # Tratamento robusto do valor mascara de real (ex: "1.250,50" -> 1250.50)
                try:
                    if valor_raw:
                        if ',' in valor_raw:
                            valor_final = float(valor_raw.replace('.', '').replace(',', '.'))
                        else:
                            valor_final = float(valor_raw)
                    else:
                        valor_final = float(plano.price)
                except (ValueError, TypeError):
                    valor_final = float(plano.price)

                # 1. Registrar Histórico
                PagamentoHistorico.objects.create(
                    aluno=aluno,
                    plano=plano,
                    valor=valor_final,
                    status='pago',
                    metodo_pagamento=metodo
                )
                
                # 2. Configurar Acesso
                from datetime import timedelta
                hoje_local = timezone.localtime(timezone.now()).date()
                base_data = hoje_local
                if hoje_local.weekday() == 6: # Domingo
                    base_data = hoje_local + timedelta(days=1)
                
                acesso.data_vencimento = base_data + timedelta(days=plano.duration_days)
                acesso.status_catraca = 'liberado'
                acesso.save()
                
                # 3. Registrar no Caixa (Se possível)
                try:
                    registrar_venda_no_caixa(
                        valor=valor_final,
                        descricao=f"Matrícula + Plano: {aluno.nome_completo} ({plano.name})",
                        metodo=metodo,
                        origem='MANUAL'
                    )
                except Exception as e:
                    messages.warning(request, "Cadastro realizado, mas não foi possível registrar no caixa (verifique se há um caixa aberto).")
                
                messages.success(request, f"Membro {aluno.nome_completo} cadastrado com Plano {plano.name}!")
            else:
                messages.success(request, f"Aluno {aluno.nome_completo} cadastrado com sucesso!")
            
            return redirect('crm_aluno_detail', aluno_id=aluno.id)

    else:
        form = AlunoForm()
    
    return render(request, 'crm/aluno_form.html', {
        'form': form,
        'gym_settings': gym_settings,
        'planos': planos,
        'title': 'Novo Membro'
    })

@login_required
def crm_aluno_edit(request, aluno_id):
    """Edição de alunos existentes"""
    from .models import Aluno, GymSetting, Plan
    from .forms import AlunoForm
    from django.shortcuts import get_object_or_404
    
    aluno = get_object_or_404(Aluno, id=aluno_id)
    
    if not request.user.has_perm('blog.can_manage_students') and not request.user.is_superuser:
        messages.error(request, "Acesso Negado: Permissão insuficiente.")
        return redirect('crm_aluno_detail', aluno_id=aluno.id)
    
    gym_settings = GymSetting.objects.first()
    planos = Plan.objects.all()
    
    if request.method == 'POST':
        form = AlunoForm(request.POST, request.FILES, instance=aluno)
        if form.is_valid():
            aluno = form.save(commit=False)
            
            # Processar imagem da webcam (Base64) se houver nova
            webcam_image = request.POST.get('webcam_image')
            if webcam_image and not request.FILES.get('foto'):
                import base64
                from django.core.files.base import ContentFile
                try:
                    format, imgstr = webcam_image.split(';base64,')
                    ext = format.split('/')[-1]
                    data = ContentFile(base64.b64decode(imgstr), name=f"aluno_webcam_{aluno.cpf}.{ext}")
                    aluno.foto = data
                except:
                    pass
            
            aluno.save()
            messages.success(request, f"Cadastro de {aluno.nome_completo} atualizado!")
            return redirect('crm_aluno_detail', aluno_id=aluno.id)
    else:
        form = AlunoForm(instance=aluno)
    
    return render(request, 'crm/aluno_form.html', {
        'form': form,
        'gym_settings': gym_settings,
        'planos': planos,
        'title': 'Editar Membro',
        'aluno': aluno
    })


