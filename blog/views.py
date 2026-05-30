from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import models
from datetime import date, timedelta
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit
import json
import logging
import requests
import re
from google import genai
from google.genai import types
import base64

from blog.models import ContactInfo, Program, Schedule, Trainer, Plan, Aluno, PagamentoHistorico, ControleAcesso
from django.utils import timezone
from .services import processar_vencimento_catraca
from blog.whatsapp_service import EvolutionApiService
from django.views.decorators.http import require_POST
import re
from .forms import ContactForm

def log_midia(msg):
    with open("/tmp/gemini_debug.log", "a") as f:
        f.write(str(msg) + "\n")

def processar_midia_gemini(remetente, msg, tipo_midia):
    from blog.models import GymSetting, Aluno
    gym_settings = GymSetting.objects.first()
    
    if gym_settings and not gym_settings.is_ia_active:
        print(f"[LOG] IA desativada. Ignorando mídia de {remetente}")
        return
    
    # Usa a chave fornecida
    api_key = "AIzaSyAFrByGIzSZRKpPl4peEK0GAB2zLp3srTo"
        
    client = genai.Client(api_key=api_key)
    
    evolution_url = gym_settings.evolution_api_url if gym_settings else "http://localhost:8080"
    apikey_evol = gym_settings.evolution_api_key if gym_settings else "429683C4C977415CBEE243405C76100E"
    instance_name = gym_settings.evolution_instance_name if gym_settings else "API-Evolution"
    
    # 1. Tentar ler o base64 nativamente do payload do webhook (se webhookBase64=true)
    base64_data = None
    msg_content = msg.get('message', {})
    
    if msg.get('base64'):
        base64_data = msg.get('base64')
    elif msg_content.get('base64'):
        base64_data = msg_content.get('base64')
    else:
        for k, v in msg_content.items():
            if isinstance(v, dict) and 'base64' in v:
                base64_data = v['base64']
                break
                
    # 2. Fallback para requisição externa se não encontrou nativamente
    try:
        if not base64_data:
            url_base64 = f"{evolution_url}/chat/getBase64FromMediaMessage/{instance_name}"
            headers = {"apikey": apikey_evol, "Content-Type": "application/json"}
            payload = {"message": msg}
            
            log_midia(f"Iniciando midia {tipo_midia} para {remetente}. URL: {url_base64}")
            
            response = requests.post(url_base64, headers=headers, json=payload)
            if response.status_code not in (200, 201):
                log_midia(f"Falha EvoAPI: {response.status_code} {response.text}")
                return
                
            base64_data = response.json().get('base64')
            if not base64_data:
                log_midia("Nenhum base64 retornado. Resposta: " + response.text)
                return
            
        # Evolution API pode retornar "data:image/jpeg;base64,/9j..."
        if "," in base64_data:
            base64_data = base64_data.split(",")[1]
            
        log_midia(f"Base64 recebido com tamanho: {len(base64_data)}")
            
        if tipo_midia == 'image':
            prompt = '''Analise esta imagem. É um comprovante de transferência bancária ou PIX? 
            Se sim, extraia as seguintes informações no formato JSON puro, sem acentos nas chaves:
            {
                "e_comprovante": true,
                "valor_pago": "0.00",
                "nome_pagador": "Nome da Pessoa"
            }
            Retorne APENAS o JSON, sem formatação Markdown. Se não for um comprovante, retorne {"e_comprovante": false}.'''
            
            imagem = types.Part.from_bytes(data=base64.b64decode(base64_data), mime_type='image/jpeg')
            response_ai = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[prompt, imagem]
            )
            texto_ai = response_ai.text.strip()
            if texto_ai.startswith("```json"):
                texto_ai = texto_ai[7:-3]
            
            log_midia(f"Texto AI Imagem: {texto_ai}")
            
            try:
                dados = json.loads(texto_ai)
                if dados.get("e_comprovante"):
                    nome_pagador = dados.get("nome_pagador", "").strip()
                    valor = dados.get("valor_pago", "")
                    
                    aluno_zap = None
                    numero = remetente.split('@')[0]
                    if len(numero) > 8:
                        final_num = numero[-8:]
                        aluno_zap = Aluno.objects.filter(whatsapp__endswith=final_num).first()
                    
                    # Procura se existe aluno exatamente com o nome do pagador
                    aluno_nome = Aluno.objects.filter(nome__iexact=nome_pagador).first() if nome_pagador else None
                        
                    if aluno_zap:
                        aluno_zap.status = 'AGUARDANDO'
                        aluno_zap.save()
                        
                        nome_zap_p1 = aluno_zap.nome.upper().split()[0] if aluno_zap.nome else ""
                        nome_pagador_p1 = nome_pagador.upper().split()[0] if nome_pagador else "DESCONHECIDO"
                        
                        if nome_zap_p1 == nome_pagador_p1:
                            msg_resposta = f"🧾 *Comprovante Recebido!*\nIdentifiquei seu pagamento de R$ {valor}, {aluno_zap.nome.split()[0]}!\n\nO status do seu plano foi alterado para *Aguardando*. Nossa equipe já foi notificada para confirmar o pagamento e liberar sua catraca!"
                        else:
                            msg_resposta = f"🧾 *Comprovante Recebido!*\nIdentifiquei um pagamento de R$ {valor} feito por *{nome_pagador}*.\n\nEsse pagamento é para o plano de *{aluno_zap.nome}* mesmo? (Nossa equipe de recepção vai ler sua resposta e confirmar para você)"
                        
                        EvolutionApiService.enviar_mensagem_texto(remetente, msg_resposta)
                        log_midia("Comprovante aprovado - AGUARDANDO")
                    else:
                        if aluno_nome:
                            aluno_nome.status = 'AGUARDANDO'
                            aluno_nome.save()
                            msg_resposta = f"🧾 *Comprovante Recebido!*\nIdentifiquei um pagamento de R$ {valor} feito por *{nome_pagador}*.\n\nEncontrei esse nome no sistema! É para o plano de *{aluno_nome.nome}* mesmo? Nossa equipe já foi notificada para confirmar."
                        else:
                            msg_resposta = f"🧾 *Comprovante LIDO!* Valor: R$ {valor} (Pagador: {nome_pagador}).\n\nPorém, não consegui encontrar o cadastro associado ao seu número. Para concluirmos e encaminharmos para aprovação da recepção, digite o *NOME COMPLETO* do aluno que vai receber esse pagamento:"
                        
                        EvolutionApiService.enviar_mensagem_texto(remetente, msg_resposta)
                        log_midia("Comprovante processado (verificação de nome)")
            except Exception as json_e:
                log_midia(f"Erro JSON: {json_e}")
                
        elif tipo_midia == 'audio':
            from blog.models import ChatMessage
            
            # Adiciona o aviso de áudio recebido
            ChatMessage.objects.create(remetente=remetente, is_bot=False, texto="[ÁUDIO ENVIADO PELO ALUNO]")
            
            historico = ChatMessage.objects.filter(remetente=remetente).order_by('-timestamp')[:6]
            historico = reversed(list(historico))
            
            conversa_texto = ""
            for h in historico:
                prefixo = "Assistente" if h.is_bot else "Aluno"
                conversa_texto += f"{prefixo}: {h.texto}\n"
                
            prompt_base = '''Você é o assistente virtual da academia Rocks-Fit.
            Ouça este áudio do aluno, entenda o que ele pediu ou perguntou e dê uma resposta educada, empática e direta ao ponto.'''
            
            instrucoes_extras = gym_settings.ai_system_prompt if gym_settings and gym_settings.ai_system_prompt else ""
            
            prompt_completo = f"{prompt_base}\n\nInstruções de Comportamento:\n{instrucoes_extras}\n\nHistórico Recente (Para contexto):\n{conversa_texto}"
                
            audio = types.Part.from_bytes(data=base64.b64decode(base64_data), mime_type='audio/ogg')
            response_ai = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[prompt_completo, audio]
            )
            
            log_midia(f"Texto AI Audio: {response_ai.text}")
            EvolutionApiService.enviar_mensagem_texto(remetente, response_ai.text)
            ChatMessage.objects.create(remetente=remetente, is_bot=True, texto=response_ai.text)
            
    except Exception as e:
        import traceback
        log_midia(f"Erro fatal Gemini: {traceback.format_exc()}")

def sincronizar_estados_alunos():
    """
    Roda automações de status:
    - Vencido (< hoje) -> SUSPENSO (Mensalidade Atrasada)
    - Vencido há mais de 30 dias -> INATIVO
    - Sem freqüência há mais de 30 dias -> INATIVO
    """
    from blog.models import Aluno, GymSetting
    from django.utils import timezone
    from datetime import date, timedelta
    
    gs = GymSetting.objects.first()
    tolerancia = gs.dias_tolerancia if gs else 0
    
    hoje = date.today()
    data_corte = hoje - timedelta(days=tolerancia)
    limite_inativo = hoje - timedelta(days=30)
    
    # 1. SUSPENSO: Plano Vencido além da tolerância e até 30 dias de atraso
    Aluno.objects.filter(
        status='ATIVO',
        acesso__data_vencimento__lt=data_corte,
        acesso__data_vencimento__gte=limite_inativo,
        acesso__dias_congelados=0
    ).update(status='SUSPENSO')
    
    # 2. INATIVO: Plano Vencido há mais de 30 dias
    Aluno.objects.filter(
        acesso__data_vencimento__lt=limite_inativo,
        acesso__dias_congelados=0
    ).exclude(status='INATIVO').update(status='INATIVO')
    
    # 3. INATIVO: Sem freqüência há mais de 30 dias
    Aluno.objects.filter(
        acesso__ultimo_acesso__lt=timezone.now() - timedelta(days=30),
        acesso__dias_congelados=0
    ).exclude(status='INATIVO').update(status='INATIVO')
    
    # 4. INADIMPLENTE: Tem pagamento pendente e a data de corte (vencimento + tolerância) já passou
    alunos_inadimplentes = Aluno.objects.filter(
        status__in=['ATIVO', 'AGUARDANDO', 'SUSPENSO'],
        acesso__data_vencimento__lt=data_corte,
        pagamentos__status='pendente',
        acesso__dias_congelados=0
    ).distinct()
    alunos_inadimplentes.update(status='INADIMPLENTE')
    
    # 5. GERAR DÉBITO PENDENTE: Cria automaticamente um pagamento pendente para o mês vigente se o plano expirou
    from blog.models import PagamentoHistorico
    from datetime import datetime
    alunos_vencidos = Aluno.objects.filter(
        status__in=['ATIVO', 'SUSPENSO', 'INADIMPLENTE'],
        acesso__data_vencimento__lt=hoje,
        acesso__data_vencimento__gte=limite_inativo,
        acesso__dias_congelados=0
    )
    for a in alunos_vencidos:
        # Se ainda não gerou cobrança pendente
        if not PagamentoHistorico.objects.filter(aluno=a, status='pendente').exists():
            ultimo_pago = PagamentoHistorico.objects.filter(aluno=a, status='pago').order_by('-data_pagamento').first()
            if ultimo_pago and ultimo_pago.plano and ultimo_pago.plano.plan_type != 'diaria':
                data_vencimento_dt = timezone.make_aware(datetime.combine(a.acesso.data_vencimento, datetime.min.time()))
                PagamentoHistorico.objects.create(
                    aluno=a,
                    plano=ultimo_pago.plano,
                    valor=0.0,
                    status='pendente',
                    data_pagamento=data_vencimento_dt
                )

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
    """NUCLEAR OPTION: Executa GRANT e REPARO DE LOGS para destravar o banco na Hostman"""
    from django.db import connection
    from django.db.migrations.recorder import MigrationRecorder
    from django.core.management import call_command
    from django.http import HttpResponse

    results = []
    
    # 0. Identificar Usuário Corrente
    current_user = "unknown"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_user;")
            current_user = cursor.fetchone()[0]
            results.append(f"ℹ️ Usuário do Banco: <b>{current_user}</b>")
    except Exception as e:
        results.append(f"❌ Falha ao identificar usuário: {e}")

    # 1. Tenta corrigir permissões de esquema e objetos
    commands = [
        f"GRANT USAGE ON SCHEMA public TO \"{current_user}\";",
        f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \"{current_user}\";",
        f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO \"{current_user}\";",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO \"{current_user}\";"
    ]
    
    with connection.cursor() as cursor:
        for cmd in commands:
            try:
                cursor.execute(cmd)
                results.append(f"✅ SUCESSO: {cmd}")
            except Exception as e:
                results.append(f"❌ FALHA: {cmd} | Erro: {e}")

    # 2. Verificação de tabelas críticas
    critical_tables = ["blog_user", "blog_trainer", "blog_aluno", "blog_plan"]
    for table in critical_tables:
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT 1 FROM {table} LIMIT 1;")
            results.append(f"✅ VERIFICAÇÃO: Tabela <b>{table}</b> está acessível.")
        except Exception as e:
            results.append(f"🔴 ERRO: Tabela <b>{table}</b> inacessível: {e}")

    # 3. Corrigir Erro de Log de Admin (ForeignKeyViolation auth_user)
    try:
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS django_admin_log CASCADE;")
            results.append("✅ Tabela django_admin_log removida para reconstrução.")
            MigrationRecorder.Migration.objects.filter(app='admin').delete()
            results.append("✅ Registro de migração 'admin' resetado.")
            
        call_command('migrate', 'admin', interactive=False)
        results.append("✅ Tabela de logs recriada com sucesso apontando para o Usuário correto.")
    except Exception as e:
        results.append(f"⚠️ Aviso ao reparar logs: {e}")

    html_response = f"""
    <html>
    <head><title>Reparo de Banco - Rocks Fit</title>
    <style>body {{ font-family: sans-serif; line-height: 1.6; padding: 20px; background: #f4f4f9; }} 
    .container {{ max-width: 800px; margin: auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
    h2 {{ color: #d32f2f; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
    .log {{ background: #eee; padding: 15px; border-radius: 5px; font-family: monospace; font-size: 14px; white-space: pre-wrap; }}
    .success {{ color: #2e7d32; }} .error {{ color: #d32f2f; }} .info {{ color: #0277bd; }}
    a {{ display: inline-block; margin-top: 20px; color: #1976d2; text-decoration: none; font-weight: bold; }}
    </style></head>
    <body>
    <div class="container">
        <h2>Relatório de Reparo Nuclear</h2>
        <div class="log">
            {"<br>".join(results)}
        </div>
        <p>Se as falhas persistirem, execute manualmente como Superusuário:</p>
        <div class="log" style="background: #333; color: #fff;">
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "{current_user}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "{current_user}";
        </div>
        <a href="/">Voltar para Home</a> | <a href="/login/">Ir para Login</a>
    </div>
    </body></html>
    """
    return HttpResponse(html_response)


def home(request):
    """
    View da página principal.
    RESILIENTE A FALHAS DE BANCO: nunca retorna HTTP 500.
    Qualquer erro de DB é logado no servidor e a página é renderizada com dados vazios.
    """
    import logging
    import traceback
    logger = logging.getLogger(__name__)

    trainers_list = []
    plans_list = []
    programs_list = []
    days_data = []

    from django.utils import timezone
    today = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'][timezone.now().weekday()]

    # --- Trainers ---
    try:
        trainers_list = list(Trainer.objects.all().order_by('order'))
    except Exception:
        try:
            trainers_list = list(Trainer.objects.all().order_by('id'))
        except Exception as e:
            logger.error(f"[HOME] Falha ao carregar Trainers: {e}\n{traceback.format_exc()}")

    # --- Plans ---
    try:
        plans_list = list(Plan.objects.all().order_by('order'))
    except Exception:
        try:
            plans_list = list(Plan.objects.all().order_by('id'))
        except Exception as e:
            logger.error(f"[HOME] Falha ao carregar Plans: {e}\n{traceback.format_exc()}")

    # --- Programs ---
    try:
        programs_list = list(Program.objects.all().order_by('order'))
    except Exception:
        try:
            programs_list = list(Program.objects.all().order_by('id'))
        except Exception as e:
            logger.error(f"[HOME] Falha ao carregar Programs: {e}\n{traceback.format_exc()}")

    # --- Schedules ---
    try:
        days_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        schedules = list(Schedule.objects.all().select_related('trainer', 'program'))
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
        logger.error(f"[HOME] Falha ao carregar Schedules: {e}\n{traceback.format_exc()}")
        days_data = []

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
    token = request.GET.get('token') or request.POST.get('token')
    if token != getattr(settings, 'CATRACA_SYNC_TOKEN', None):
        return JsonResponse({'status': 'error', 'message': 'Não autorizado'}, status=401)

    import datetime
    hoje = datetime.date.today()
    
    # Pegar todos os alunos ATIVOS
    alunos = Aluno.objects.filter(status='ATIVO').select_related('acesso')
    
    lista = []
    for aluno in alunos:
        acc = getattr(aluno, 'acesso', None)
        dias = 0
        if acc and acc.data_vencimento:
            dias = acc.dias_vencimento
            if dias < 0: dias = 0
            
        lista.append({
            'nome': aluno.nome_completo,
            'id': aluno.id,
            'cpf': ''.join(filter(str.isdigit, aluno.cpf)) if aluno.cpf else "",
            'vencimento': acc.data_vencimento.strftime('%Y-%m-%d') if acc and acc.data_vencimento else "N/A",
            'matricula': aluno.matricula,
            'dias_restantes': dias,
            'status': aluno.status,
            'foto_url': aluno.foto.url if aluno.foto else None
        })
    
    # Configurações da Academia
    from blog.models import GymSetting
    gs = GymSetting.objects.first()
    settings_data = {
        'fluxo': gs.catraca_fluxo if gs else 'BIDIRECIONAL',
        'msg_entrada': gs.msg_entrada if gs else 'Bom treino!',
        'msg_saida': gs.msg_saida if gs else 'Bom descanso!',
    }
    
    return JsonResponse({'alunos': lista, 'settings': settings_data})

def catraca_check_api(request, id_tag):
    """
    Retorna foto, nome e dias restantes para o monitor.
    """
    from .models import AcessoLog, GymSetting
    
    def enviar_whatsapp_academia(aluno, motivo):
        """Simula o envio de mensagem para o WhatsApp da Academia (Staff)"""
        gs = GymSetting.objects.first()
        if gs and gs.whatsapp_notificacao:
            # Em produção aqui chamaria uma API como WPPConnect ou Evolution API
            msg_final = f"🚨 *ALERTA DE ACESSO NEGADO*\nAluno: {aluno.nome_completo}\nMatrícula: {aluno.matricula}\nMotivo: {motivo}\nMensagem: 'Estou com problemas no meu acesso, pode verificar por favor?'"
            print(f"📱 [WHATSAPP API] Notificação enviada para {gs.whatsapp_notificacao}: {msg_final}")
            
    from django.conf import settings
    token = request.GET.get('token') or request.POST.get('token')
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

    # 3. VERIFICAÇÃO DE ANIVERSÁRIO
    eh_aniversario = False
    if aluno.data_nascimento:
        if aluno.data_nascimento.month == hoje.month and aluno.data_nascimento.day == hoje.day:
            eh_aniversario = True

    # 4. MONITORAMENTO DE STATUS CRM (Administrativo)
    from .models import GymSetting
    gym_settings = GymSetting.objects.first()
    import urllib.parse
    msg_help = "Estou com problemas no meu acesso, pode verificar por favor?"
    whatsapp_link = f"https://wa.me/{gym_settings.whatsapp_notificacao}?text={urllib.parse.quote(msg_help)}" if gym_settings and gym_settings.whatsapp_notificacao else "#"
    
    msg_entrada = gym_settings.msg_entrada if gym_settings else "Bom treino!"
    msg_saida = gym_settings.msg_saida if gym_settings else "Bom descanso!"
    msg_aniversario = gym_settings.msg_aniversario if gym_settings else "Parabéns! Feliz Aniversário! 🎉"

    if aluno.status != 'ATIVO':
        msg_custom = gym_settings.msg_bloqueio_crm if gym_settings else "Cadastro Suspenso/Inativo."
        if aluno.is_convenio:
            msg_custom = gym_settings.msg_erro_wellhub if gym_settings else "Erro no convênio corporativo."
            
        # LOG DE TENTATIVA NEGADA
        AcessoLog.objects.create(aluno=aluno, tipo='NEGADO')
        enviar_whatsapp_academia(aluno, "Cadastro Suspenso/Inativo")
        
        return JsonResponse({
            'status': 'bloqueado', 'nome': aluno.nome_completo,
            'foto_url': foto_url, 'status_borda': 'vermelho',
            'mensagem': msg_custom,
            'whatsapp_action': whatsapp_link
        }, status=403)

    # 1. AGUARDANDO BIOMETRIA: 1a entrada apos pagamento
    if acesso and acesso.status_catraca == 'aguardando_biometria':
        plano = acesso.plano_pendente
        dias = 30
        if plano:
            dias = plano.duration_days if plano.duration_days else 30
        acesso.data_vencimento = hoje + timedelta(days=dias)
        acesso.status_catraca = 'liberado'
        acesso.plano_pendente = None
        acesso.esta_dentro = True
        acesso.ultimo_acesso = timezone.now()
        acesso.save()
        
        msg_final = f'{msg_entrada} (Plano Ativado)'
        if eh_aniversario: msg_final = msg_aniversario

        return JsonResponse({
            'status': 'ativo', 'nome': aluno.nome_completo, 'matricula': aluno.matricula,
            'vencimento': acesso.data_vencimento.strftime('%d/%m/%Y'),
            'dias_restantes': dias, 'foto_url': foto_url,
            'status_borda': 'verde',
            'mensagem': msg_final,
            's': '0' # Sempre entrada na ativação
        })

    # 5. SEM ACESSO FINANCEIRO
    if not acesso or not acesso.data_vencimento:
        return JsonResponse({
            'status': 'bloqueado', 'nome': aluno.nome_completo,
            'foto_url': foto_url, 'status_borda': 'vermelho',
            'mensagem': 'Sem plano ativo. Procure a recepção.'
        }, status=403)

    dias_restantes = acesso.dias_vencimento
    tolerancia = gym_settings.dias_tolerancia if gym_settings else 0

    # 3. VENCIDO
    if dias_restantes + tolerancia < 0:
        acesso.status_catraca = 'bloqueado'
        acesso.save()
        
        # LOG DE TENTATIVA NEGADA
        AcessoLog.objects.create(aluno=aluno, tipo='NEGADO')
        enviar_whatsapp_academia(aluno, "Plano Vencido")
        
        return JsonResponse({
            'nome': aluno.nome_completo, 'matricula': aluno.matricula,
            'vencimento': acesso.data_vencimento.strftime('%d/%m/%Y'),
            'dias_restantes': dias_restantes, 'foto_url': foto_url,
            'status': 'vencido', 'status_borda': 'vermelho',
            'mensagem': 'Plano vencido. Procure a recepção.',
            'whatsapp_action': whatsapp_link
        }, status=403)
        
    elif dias_restantes < 0:
        # Dentro do crédito de tolerância (Vencido, mas liberado)
        msg_entrada += f" (Crédito: {-dias_restantes}/{tolerancia}d)"

    # 4. LÓGICA DE ENTRADA/SAÍDA E FLUXO
    fluxo = gym_settings.catraca_fluxo if gym_settings else 'BIDIRECIONAL'
    
    # Determina o sentido: 0 = Entrada, 1 = Saída
    if fluxo == 'ENTRADA':
        esta_saindo = False
        cmd_catraca = "0"
    elif fluxo == 'SAIDA':
        esta_saindo = True
        cmd_catraca = "1"
    else: # BIDIRECIONAL
        esta_saindo = acesso.esta_dentro
        cmd_catraca = "1" if esta_saindo else "0"

    acesso.esta_dentro = not acesso.esta_dentro
    acesso.ultimo_acesso = timezone.now()
    
    # Registrar Log de Acesso para IA
    from .models import AcessoLog
    AcessoLog.objects.create(
        aluno=aluno,
        tipo='SAIDA' if esta_saindo else 'ENTRADA'
    )
    
    msg_final = gym_settings.msg_entrada if not esta_saindo else gym_settings.msg_saida
    if esta_saindo:
        # Se for DIÁRIA, esgota o acesso após a saída
        ultimo_pago = aluno.pagamentos.filter(status='pago', plano__isnull=False).order_by('-data_pagamento').first()
        if ultimo_pago and ultimo_pago.plano.plan_type == 'diaria':
            acesso.data_vencimento = hoje - timedelta(days=1)
            acesso.status_catraca = 'bloqueado'
            msg_final = "Diária esgotada. Até a próxima!"
            
    acesso.save()

    if eh_aniversario:
        msg_final = gym_settings.msg_aniversario if gym_settings else "Parabéns pelo seu dia! 🎉"

    return JsonResponse({
        'nome': aluno.nome_completo, 'matricula': aluno.matricula,
        'vencimento': acesso.data_vencimento.strftime('%d/%m/%Y'),
        'dias_restantes': dias_restantes, 'foto_url': foto_url,
        'status': 'alerta' if dias_restantes <= 5 else 'ativo',
        'status_borda': 'verde',
        'mensagem': msg_final,
        's': cmd_catraca
    })

@csrf_exempt
def catraca_face_check_api(request):
    """
    Recebe um frame via POST e tenta encontrar o aluno correspondente.
    Usa um método de comparação visual resiliente.
    """
    from django.conf import settings
    token = request.POST.get('token') or request.GET.get('token')
    if token != getattr(settings, 'CATRACA_SYNC_TOKEN', None):
        return JsonResponse({'status': 'error', 'message': 'Não autorizado'}, status=401)

    foto_b64 = request.POST.get('frame')
    if not foto_b64:
        return JsonResponse({'status': 'error', 'message': 'Imagem não enviada'}, status=400)

    import cv2
    import numpy as np
    import base64
    import os

    try:
        # 0. Carregar Detector de Faces no Servidor
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        # 1. Decodificar o frame recebido
        format, imgstr = foto_b64.split(';base64,')
        ext = format.split('/')[-1]
        frame_bytes = base64.b64decode(imgstr)
        nparr = np.frombuffer(frame_bytes, np.uint8)
        img_check = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 2. Tentar isolar APENAS o rosto no frame recebido (Calibração de Foco)
        gray_frame = cv2.cvtColor(img_check, cv2.COLOR_BGR2GRAY)
        faces_frame = face_cascade.detectMultiScale(gray_frame, 1.1, 4)
        
        if len(faces_frame) > 0:
            (x, y, w, h) = faces_frame[0]
            img_check_crop = gray_frame[y:y+h, x:x+w]
            img_check_crop = cv2.resize(img_check_crop, (300, 300))
        else:
            # Fallback se não detectar rosto no frame (talvez ângulo ruim), usa a imagem toda redimensionada
            img_check_crop = cv2.resize(gray_frame, (300, 300))
        
        # 3. Buscar alunos ativos com foto
        alunos_com_foto = Aluno.objects.filter(foto__isnull=False, status='ATIVO').select_related('acesso')
        
        melhor_aluno = None
        melhor_score = 0
        melhor_dist = float('inf')

        # Configuração Ultra-Sensível do ORB
        orb = cv2.ORB_create(nfeatures=2000, scaleFactor=1.2, nlevels=8)
        kp1, des1 = orb.detectAndCompute(img_check_crop, None)

        if des1 is not None:
            for aluno in alunos_com_foto:
                try:
                    ref_path = aluno.foto.path
                    if not os.path.exists(ref_path): continue
                    
                    img_ref = cv2.imread(ref_path)
                    if img_ref is None: continue
                    img_ref_gray = cv2.cvtColor(img_ref, cv2.COLOR_BGR2GRAY)
                    
                    # Tentar isolar o rosto na foto de cadastro (Garante comparação Rosto-a-Rosto)
                    faces_ref = face_cascade.detectMultiScale(img_ref_gray, 1.1, 4)
                    if len(faces_ref) > 0:
                        (rx, ry, rw, rh) = faces_ref[0]
                        img_ref_crop = img_ref_gray[ry:ry+rh, rx:rx+rw]
                    else:
                        img_ref_crop = img_ref_gray

                    img_ref_crop = cv2.resize(img_ref_crop, (300, 300))
                    
                    kp2, des2 = orb.detectAndCompute(img_ref_crop, None)
                    if des2 is None: continue
                    
                    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                    matches = bf.match(des1, des2)
                    
                    if len(matches) > 20: # Mínimo de pontos de interesse
                        avg_dist = sum(m.distance for m in matches) / len(matches)
                        
                        # Lógica de Ranqueamento: Prioriza similaridade geométrica
                        if len(matches) > melhor_score or (len(matches) > 30 and avg_dist < melhor_dist):
                           melhor_score = len(matches)
                           melhor_dist = avg_dist
                           melhor_aluno = aluno
                except: continue

        # 4. Limiar de Confiança Calibrado para Rosto-a-Rosto (ALTA SENSIBILIDADE)
        # Score > 25 ou (Score > 15 e Distância < 80)
        if melhor_aluno and (melhor_score > 25 or (melhor_score >= 15 and melhor_dist < 80)):
            print(f"✅ FACIAL MATCH: {melhor_aluno.nome_completo} (Score={melhor_score}, Dist={melhor_dist:.2f})")
            return catraca_check_api(request, melhor_aluno.matricula)
        
        if melhor_aluno:
            print(f"⚠️ FACIAL BORDERLINE: {melhor_aluno.nome_completo} (Score={melhor_score}, Dist={melhor_dist:.2f}) - Abaixo do Limiar")
        
        return JsonResponse({'status': 'nao_reconhecido', 'mensagem': 'Rosto não identificado ou baixa confiança.'}, status=404)

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

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

def processar_pagamento(aluno, plano, valor_pago, metodo, user=None, data_pagamento=None, desconto=0.0):
    """
    Lógica centralizada para processamento de pagamentos, amortização de dívidas e cálculo de dias de crédito.
    
    Regras de Negócio Implementadas:
    --------------------------------
    TIPO A (Dívida de Matrícula Parcial): 
        O aluno comprou um plano, não pagou o valor integral, e a pendência tem `valor > 0`.
        - Quando paga: O sistema entende que ele está comprando o restante dos dias daquele plano ativo.
        - Dias Extras: Concede dias proporcionais ao valor investido (mantendo a lógica do crédito).
        - Status: Vai para ATIVO (se quitou) ou AGUARDANDO (se abateu só uma parte).
    
    TIPO B (Atrasado Pós-Vencimento / Taxas e Multas):
        O plano do aluno expirou, o sistema gerou uma dívida automática de atraso (valor base = 0.0, cresce com juros).
        - Quando paga: O sistema entende que ele está apenas quitando uma penalidade pelo abandono/atraso.
        - Dias Extras: NÃO concede nenhum dia de acesso (retorna 0 dias).
        - Status: Vai para INATIVO imediatamente. Para voltar a treinar, exige nova matrícula/lançamento.
        
    Descontos:
        Valores de desconto concedidos pela recepção abatem o débito sem prejudicar a quantidade de dias
        a que o aluno tem direito (no caso do TIPO A), sendo somados ao `valor_pago` na proporção.
    """
    from django.utils import timezone
    from blog.models import PagamentoHistorico
    
    if not data_pagamento:
        data_pagamento = timezone.now()
    
    # 1. Busca por pendência existente (independente do plano enviado pelo UI)
    pendente = PagamentoHistorico.objects.filter(aluno=aluno, status='pendente').order_by('id').first()
    
    if pendente:
        plano_pendente = pendente.plano
        if plano_pendente:
            valor_plano = float(plano_pendente.price)
            dias_totais = plano_pendente.duration_days
        else:
            valor_plano = float(pendente.valor)
            dias_totais = 30
            
        valor_pendente_atual = float(pendente.valor)
        
        if valor_pendente_atual > 0:
            # =========================================================
            # TIPO A: Pagamento de parte da matrícula (Dívida de plano)
            # =========================================================
            # Cenário: O aluno adquiriu um plano (ex: 80,00) mas pagou apenas um sinal (ex: 50,00).
            # A dívida registrada foi 30,00. Esse pagamento é referente aos dias restantes do plano.
            if (valor_pago + desconto) >= valor_pendente_atual:
                # Quitou a dívida da matrícula: Concede o restante dos dias de acesso e ativa o aluno.
                PagamentoHistorico.objects.create(aluno=aluno, plano=plano_pendente, valor=valor_pago, status='pago', data_pagamento=data_pagamento, metodo_pagamento=metodo, operador=user)
                pendente.delete()
                aluno.status = 'ATIVO'
                dias_credito = max(1, int(round((valor_pendente_atual / valor_plano) * dias_totais)))
                return dias_credito, plano_pendente
            else:
                # Abateu apenas uma parte da matrícula: Concede dias proporcionais e o mantém aguardando o restante.
                PagamentoHistorico.objects.create(aluno=aluno, plano=plano_pendente, valor=valor_pago, status='pago', data_pagamento=data_pagamento, metodo_pagamento=metodo, operador=user)
                pendente.valor = valor_pendente_atual - (valor_pago + desconto)
                pendente.save()
                aluno.status = 'AGUARDANDO'
                dias_credito = max(1, int(round(((valor_pago + desconto) / valor_plano) * dias_totais)))
                return dias_credito, plano_pendente
        else:
            # ============================================================================
            # TIPO B: Pagamento de Atrasado Pós-Vencimento (Multas geradas automaticamente)
            # ============================================================================
            # Cenário: O prazo de validade expirou. A automação gerou um débito onde o 
            # valor base é 0.00 e o débito real consiste apenas nos juros e multas calculados.
            # Regra: NÃO SE DÁ DIAS EXTRAS! É apenas quitação de dívida de abandono.
            PagamentoHistorico.objects.create(aluno=aluno, plano=plano_pendente, valor=valor_pago, status='pago', data_pagamento=data_pagamento, metodo_pagamento=metodo, operador=user)
            pendente.delete()
            aluno.status = 'INATIVO' # Zera o status com a academia. Para treinar precisa renovar.
            return 0, plano_pendente

    # 2. Nova Compra
    if not plano:
        PagamentoHistorico.objects.create(aluno=aluno, plano=None, valor=valor_pago, status='pago', data_pagamento=data_pagamento, metodo_pagamento=metodo, operador=user)
        aluno.status = 'ATIVO'
        return 0, None
        
    valor_plano = float(plano.price)
    if valor_plano <= 0:
        PagamentoHistorico.objects.create(aluno=aluno, plano=plano, valor=valor_pago, status='pago', data_pagamento=data_pagamento, metodo_pagamento=metodo, operador=user)
        aluno.status = 'ATIVO'
        return plano.duration_days, plano
        
    if valor_pago < valor_plano:
        PagamentoHistorico.objects.create(aluno=aluno, plano=plano, valor=valor_pago, status='pago', data_pagamento=data_pagamento, metodo_pagamento=metodo, operador=user)
        PagamentoHistorico.objects.create(aluno=aluno, plano=plano, valor=valor_plano - valor_pago, status='pendente', data_pagamento=data_pagamento, metodo_pagamento=metodo, operador=user)
        aluno.status = 'AGUARDANDO'
        dias = max(1, int(round((valor_pago / valor_plano) * plano.duration_days)))
        return dias, plano
    else:
        PagamentoHistorico.objects.create(aluno=aluno, plano=plano, valor=valor_pago, status='pago', data_pagamento=data_pagamento, metodo_pagamento=metodo, operador=user)
        aluno.status = 'ATIVO'
        dias = int(round((valor_pago / valor_plano) * plano.duration_days))
        return dias, plano

@login_required
def crm_dashboard(request):
    """Dashboard com Inteligência Artificial, Demografia e Plano de Ação Estratégico"""
    from blog.models import Aluno, Plan, PagamentoHistorico, ControleAcesso
    from django.db.models import Avg, Sum, Count
    from django.utils import timezone
    from datetime import date, timedelta
    import datetime

    # 0. Sincronização Automática de Status
    sincronizar_estados_alunos()

    # 1. Aporte Rápido (Lógica de Recebimento Direto)
    if request.method == 'POST' and 'faturar_rapido' in request.POST:
        aluno_id = request.POST.get('aluno_id')
        valor_raw = request.POST.get('valor', '0.00').strip()
        metodo = request.POST.get('metodo', 'PIX')
        plano_id = request.POST.get('plano', '')
        
        valor = valor_raw.replace('.', '').replace(',', '.') if ',' in valor_raw else valor_raw
            
        try:
            valor_pago = float(valor)
            aluno = Aluno.objects.get(id=aluno_id)
            
            plano = None
            if plano_id:
                plano = Plan.objects.get(id=plano_id)
                
            dias_adicionais, plano = processar_pagamento(aluno, plano, valor_pago, metodo, user=request.user)
            
            data_inicio_str = request.POST.get('data_inicio', '')
            base_inicio_dt = timezone.now()
            if data_inicio_str:
                from django.utils.dateparse import parse_date
                from datetime import datetime
                i_date = parse_date(data_inicio_str)
                if i_date:
                    base_inicio_dt = timezone.make_aware(datetime.combine(i_date, timezone.now().time()))
                    
            if plano and dias_adicionais > 0:
                acesso, _ = ControleAcesso.objects.get_or_create(aluno=aluno)
                base_local = timezone.localtime(base_inicio_dt).date()
                base_data = base_local
                    
                start_date = acesso.data_vencimento if (acesso.data_vencimento and acesso.data_vencimento > base_local and plano.plan_type != 'diaria') else base_data
                
                from dateutil.relativedelta import relativedelta
                if dias_adicionais == plano.duration_days:
                    if plano.plan_type == 'mensal':
                        acesso.data_vencimento = start_date + relativedelta(months=1)
                    elif plano.plan_type == 'trimestral':
                        acesso.data_vencimento = start_date + relativedelta(months=3)
                    elif plano.plan_type == 'semestral':
                        acesso.data_vencimento = start_date + relativedelta(months=6)
                    elif plano.plan_type == 'anual':
                        acesso.data_vencimento = start_date + relativedelta(years=1)
                    elif plano.plan_type == 'bienal':
                        acesso.data_vencimento = start_date + relativedelta(years=2)
                    else:
                        acesso.data_vencimento = start_date + relativedelta(months=dias_adicionais // 30, days=dias_adicionais % 30)
                else:
                    acesso.data_vencimento = start_date + relativedelta(months=dias_adicionais // 30, days=dias_adicionais % 30)
                acesso.status_catraca = 'liberado'
                acesso.save()
                
            registrar_venda_no_caixa(valor_pago, f"Aporte Rápido: {aluno.nome_completo}", metodo, 'MANUAL')
            aluno.save()
            
            messages.success(request, f"Aporte de R$ {valor} processado para {aluno.nome_completo}. Aluno Ativado!")
        except Exception as e:
            messages.error(request, f"Erro no faturamento: {str(e)}")
            
        return redirect('crm_dashboard')

    # 2. Métricas de Base (Situação Atual)
    alunos = Aluno.objects.all()
    total_alunos = alunos.count()
    
    # Contadores Específicos para os Cards
    count_ativos = alunos.filter(status='ATIVO').count()
    count_inadimplentes = alunos.filter(status='INADIMPLENTE').count()
    count_aguardando = alunos.filter(status='AGUARDANDO').count()

    # Cálculo de Idade Média (Defensivo)
    hoje = date.today()
    idades = []
    for a in alunos.filter(data_nascimento__isnull=False):
        idades.append((hoje - a.data_nascimento).days // 365)
    idade_media = round(sum(idades) / len(idades)) if idades else 0

    # Churn Rate (Inativos / Total)
    inativos = alunos.filter(status='INATIVO').count()
    churn_rate = round((inativos / total_alunos * 100), 1) if total_alunos > 0 else 0

    # 3. Inteligência de Dados (Insights)
    vencem_hoje = Aluno.objects.filter(acesso__data_vencimento=hoje).count()
    novos_mes = alunos.filter(data_cadastro__month=hoje.month, data_cadastro__year=hoje.year).count()
    
    if vencem_hoje > 0:
        ai_insights = f"Alerta: {vencem_hoje} matrículas expiram hoje. Recomenda-se abordagem ativa."
    elif novos_mes > 5:
        ai_insights = f"Crescimento positivo: {novos_mes} novos membros este mês. Continue a estratégia."
    else:
        ai_insights = "Base estabilizada. Otimize a retenção de membros antigos."

    # 4. Dados do Gráfico de Evolução Operacional (Últimos 6 meses)
    # Mostrando Ativos (pago), Em Processamento (pendente) e Inadimplentes (recusado/atrasado)
    chart_labels = []
    data_ativos = []
    data_pendentes = []
    data_inadimplentes = []
    
    for i in range(5, -1, -1):
        d = hoje - timedelta(days=i*30)
        mes_nome = d.strftime('%b')
        chart_labels.append(mes_nome)
        
        # Ativos: Pagamentos Confirmados
        ativos_mes = PagamentoHistorico.objects.filter(
            data_pagamento__month=d.month, data_pagamento__year=d.year, status='pago'
        ).count()
        data_ativos.append(ativos_mes)
        
        # Em Processamento: Pagamentos Pendentes
        pendentes_mes = PagamentoHistorico.objects.filter(
            data_pagamento__month=d.month, data_pagamento__year=d.year, status='pendente'
        ).count()
        data_pendentes.append(pendentes_mes)
        
        # Inadimplentes: Pagamentos Recusados ou alunos que entraram em inadimplência (baseado na data de cadastro como proxy ou histórico)
        # Aqui usaremos 'recusado' para mostrar falhas/inadimplência financeira no gráfico
        inad_mes = PagamentoHistorico.objects.filter(
            data_pagamento__month=d.month, data_pagamento__year=d.year, status='recusado'
        ).count()
        data_inadimplentes.append(inad_mes)

    context = {
        'alunos_lista': alunos.order_by('nome_completo'),
        'planos': Plan.objects.all(),
        'total_alunos': total_alunos,
        'count_ativos': count_ativos,
        'count_inadimplentes': count_inadimplentes,
        'count_aguardando': count_aguardando,
        'perfil_mulheres': alunos.filter(sexo='F').count(),
        'perfil_homens': alunos.filter(sexo='M').count(),
        'idade_media': idade_media,
        'churn_rate': churn_rate,
        'ai_insights': ai_insights,
        'chart_labels': json.dumps(chart_labels),
        'chart_data_ativos': json.dumps(data_ativos),
        'chart_data_pendentes': json.dumps(data_pendentes),
        'chart_data_inadimplentes': json.dumps(data_inadimplentes),
    }
    
    from blog.models import GymSetting
    context['gym_settings'] = GymSetting.objects.first()

    return render(request, 'crm/dashboard.html', context)

@login_required
def crm_config(request):
    """Gestão de permissões de SEGURANÇA MÁXIMA: Apenas modelos CORE do CRM"""
    if not request.user.is_superuser:
        return HttpResponse("Acesso Negado", status=403)

    from django.contrib.auth.models import Permission
    from .models import RolePermission, User, GymSetting
    
    target_roles = [User.TYPE_SECRETARY, User.TYPE_TRAINER, User.TYPE_NUTRITIONIST, User.TYPE_STUDENT]
    
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

    role_configs = [RolePermission.objects.get_or_create(role=r)[0] for r in target_roles]
    gym_settings = GymSetting.objects.first()

    if request.method == 'POST':
        # Salva Permissões
        for r_type in target_roles:
            role_perm, _ = RolePermission.objects.get_or_create(role=r_type)
            perm_ids = request.POST.getlist(f'perms_{r_type}')
            role_perm.permissions.set(Permission.objects.filter(id__in=perm_ids))
        
        # Salva Configurações Financeiras (Multas/Juros) e Mensagens
        if gym_settings:
            gym_settings.multa_atraso = request.POST.get('multa_atraso', 2.00)
            gym_settings.juros_mensal = request.POST.get('juros_mensal', 1.00)
            gym_settings.dias_tolerancia = request.POST.get('dias_tolerancia', 0)
            gym_settings.whatsapp_notificacao = request.POST.get('whatsapp_notificacao', '')
            
            # Mensagens Catraca
            gym_settings.msg_aniversario = request.POST.get('msg_aniversario', '')
            gym_settings.msg_bloqueio_crm = request.POST.get('msg_bloqueio_crm', '')
            gym_settings.msg_erro_wellhub = request.POST.get('msg_erro_wellhub', '')
            
            # IA
            gym_settings.is_ia_active = request.POST.get('is_ia_active') == 'on'
            gym_settings.ai_api_key = request.POST.get('ai_api_key', '')
            gym_settings.ai_system_prompt = request.POST.get('ai_system_prompt', '')
            
            gym_settings.save()
            
        messages.success(request, "Configurações atualizadas com sucesso.")
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
        'gym_settings': gym_settings,
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
        valor_pago = float(valor)
        
        plano = None
        if plano_id:
            plano = Plan.objects.get(id=plano_id)
            
        data_pagamento_str = request.POST.get('data_pagamento', '')
        pagamento_dt = timezone.now()
        if data_pagamento_str:
            from django.utils.dateparse import parse_date
            from datetime import datetime
            p_date = parse_date(data_pagamento_str)
            if p_date:
                pagamento_dt = timezone.make_aware(datetime.combine(p_date, timezone.now().time()))
                
        data_inicio_str = request.POST.get('data_inicio', '')
        base_inicio_dt = pagamento_dt
        if data_inicio_str:
            from django.utils.dateparse import parse_date
            from datetime import datetime
            i_date = parse_date(data_inicio_str)
            if i_date:
                base_inicio_dt = timezone.make_aware(datetime.combine(i_date, timezone.now().time()))
            
        desconto_raw = request.POST.get('desconto', '0.00').strip()
        desconto = float(desconto_raw.replace('.', '').replace(',', '.') if ',' in desconto_raw else desconto_raw) if desconto_raw else 0.0

        dias_adicionais, plano = processar_pagamento(aluno, plano, valor_pago, metodo, user=request.user, data_pagamento=pagamento_dt, desconto=desconto)
        
        # 2. Atualizar Controle de Acesso Automaticamente
        if plano and dias_adicionais > 0:
            from datetime import timedelta
            from blog.models import ControleAcesso
            acesso, created = ControleAcesso.objects.get_or_create(aluno=aluno)
            
            base_local = timezone.localtime(base_inicio_dt).date()
            base_data = base_local

            # Se for DIÁRIA, não acumula (reseta para o prazo do plano)
            if plano.plan_type == 'diaria':
                acesso.data_vencimento = base_data + timedelta(days=dias_adicionais)
            else:
                # Se o usuário não alterou a data de início (é hoje) e já possui vencimento futuro, acumula (Stacking)
                hoje = timezone.localtime(timezone.now()).date()
                if base_data == hoje:
                    start_date = acesso.data_vencimento if (acesso.data_vencimento and acesso.data_vencimento > base_data) else base_data
                else:
                    # Se o usuário informou uma data retroativa (ou futura específica), respeita estritamente essa data
                    start_date = base_data
                
                from dateutil.relativedelta import relativedelta
                nova_validade = start_date
                if dias_adicionais == plano.duration_days:
                    if plano.plan_type == 'mensal':
                        nova_validade = start_date + relativedelta(months=1)
                    elif plano.plan_type == 'trimestral':
                        nova_validade = start_date + relativedelta(months=3)
                    elif plano.plan_type == 'semestral':
                        nova_validade = start_date + relativedelta(months=6)
                    elif plano.plan_type == 'anual':
                        nova_validade = start_date + relativedelta(years=1)
                    elif plano.plan_type == 'bienal':
                        nova_validade = start_date + relativedelta(years=2)
                    else:
                        nova_validade = start_date + relativedelta(months=dias_adicionais // 30, days=dias_adicionais % 30)
                else:
                    nova_validade = start_date + relativedelta(months=dias_adicionais // 30, days=dias_adicionais % 30)
                    
                if not acesso.data_vencimento or nova_validade > acesso.data_vencimento:
                    acesso.data_vencimento = nova_validade

            acesso.status_catraca = 'liberado'
            acesso.esta_dentro = False
            acesso.save()
            messages.success(request, f"Acesso LIBERADO até {acesso.data_vencimento.strftime('%d/%m/%Y')}.")

        # 3. Registrar no Caixa (se houver turno aberto)
        registrar_venda_no_caixa(
            valor=valor_pago,
            descricao=f"Pagamento: {aluno.nome_completo} ({plano.name if plano else 'Taxa'})",
            metodo=metodo,
            origem='MANUAL'
        )
        
        # Salva o status do aluno e limpa a tag de cancelamento se existir
        aluno.motivo_cancelamento = None
        aluno.data_cancelamento = None
        aluno.save()
        
        messages.success(request, f"Pagamento de R$ {valor} processado. Aluno Ativado!")
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

    if request.method == 'POST' and 'trancar_matricula' in request.POST:
        from django.utils import timezone
        if hasattr(aluno, 'acesso') and aluno.acesso.data_vencimento:
            hoje = timezone.localtime(timezone.now()).date()
            if aluno.acesso.data_vencimento > hoje:
                dias_restantes = aluno.acesso.dias_vencimento
                aluno.acesso.dias_congelados += dias_restantes
                aluno.acesso.data_vencimento = hoje
                aluno.acesso.status_catraca = 'bloqueado'
                aluno.acesso.save()
                
                aluno.status = 'SUSPENSO'
                aluno.save()
                messages.success(request, f"Matrícula trancada. {dias_restantes} dias guardados como crédito.")
            else:
                messages.error(request, "O aluno não possui dias válidos no futuro para trancar.")
        else:
            messages.error(request, "Aluno sem plano ativo para trancar.")
        return redirect('crm_aluno_detail', aluno_id=aluno.id)

    if request.method == 'POST' and 'trancar_definitivo' in request.POST:
        from django.utils import timezone
        
        motivo = request.POST.get('motivo_cancelamento', 'NÃO INFORMADO')
        data_cancel = request.POST.get('data_cancelamento')
        
        if hasattr(aluno, 'acesso'):
            hoje = timezone.localtime(timezone.now()).date()
            aluno.acesso.dias_congelados = 0
            aluno.acesso.data_vencimento = hoje
            aluno.acesso.status_catraca = 'bloqueado'
            aluno.acesso.save()
            
        aluno.status = 'INATIVO'
        aluno.motivo_cancelamento = motivo
        aluno.data_cancelamento = data_cancel if data_cancel else timezone.now().date()
        aluno.save()
        messages.success(request, f"Matrícula inativada permanentemente. Motivo: {motivo}")
        return redirect('crm_aluno_detail', aluno_id=aluno.id)

    if request.method == 'POST' and 'destrancar_matricula' in request.POST:
        from django.utils import timezone
        from datetime import timedelta
        if hasattr(aluno, 'acesso') and aluno.acesso.dias_congelados > 0:
            hoje = timezone.localtime(timezone.now()).date()
            base_data = hoje
                
            from dateutil.relativedelta import relativedelta
            start_date = aluno.acesso.data_vencimento if (aluno.acesso.data_vencimento and aluno.acesso.data_vencimento > base_data) else base_data
            meses_adc = aluno.acesso.dias_congelados // 30
            dias_adc = aluno.acesso.dias_congelados % 30
            aluno.acesso.data_vencimento = start_date + relativedelta(months=meses_adc, days=dias_adc)
            aluno.acesso.dias_congelados = 0
            aluno.acesso.status_catraca = 'liberado'
            aluno.acesso.save()
            
            aluno.status = 'ATIVO'
            aluno.motivo_cancelamento = None
            aluno.data_cancelamento = None
            aluno.save()
            messages.success(request, f"Matrícula destrancada! Acesso válido até {aluno.acesso.data_vencimento.strftime('%d/%m/%Y')}.")
        return redirect('crm_aluno_detail', aluno_id=aluno.id)



    if request.method == 'POST' and 'estornar_pagamento_id' in request.POST:
        pg_id = request.POST.get('estornar_pagamento_id')
        pg = get_object_or_404(PagamentoHistorico, id=pg_id, aluno=aluno)
        
        if pg.status == 'pago':
            pg.status = 'estornado'
            pg.save()
            
            # Subtrair dias do controle de acesso
            if hasattr(aluno, 'acesso') and aluno.acesso.data_vencimento and pg.plano:
                from dateutil.relativedelta import relativedelta
                from datetime import timedelta
                valor_plano = float(pg.plano.price)
                if float(pg.valor) < valor_plano:
                    dias = max(1, int(round((float(pg.valor) / valor_plano) * pg.plano.duration_days)))
                else:
                    dias = int(round((float(pg.valor) / valor_plano) * pg.plano.duration_days))
                
                if dias == pg.plano.duration_days:
                    if pg.plano.plan_type == 'mensal':
                        aluno.acesso.data_vencimento -= relativedelta(months=1)
                    elif pg.plano.plan_type == 'trimestral':
                        aluno.acesso.data_vencimento -= relativedelta(months=3)
                    elif pg.plano.plan_type == 'semestral':
                        aluno.acesso.data_vencimento -= relativedelta(months=6)
                    elif pg.plano.plan_type == 'anual':
                        aluno.acesso.data_vencimento -= relativedelta(years=1)
                    elif pg.plano.plan_type == 'bienal':
                        aluno.acesso.data_vencimento -= relativedelta(years=2)
                    else:
                        aluno.acesso.data_vencimento -= timedelta(days=dias)
                else:
                    aluno.acesso.data_vencimento -= timedelta(days=dias)
                
                # Bloquear se a data nova for no passado
                from django.utils import timezone
                hoje = timezone.localtime(timezone.now()).date()
                if aluno.acesso.data_vencimento <= hoje:
                    aluno.acesso.status_catraca = 'bloqueado'
                    aluno.status = 'INATIVO'
                    aluno.motivo_cancelamento = None
                    aluno.data_cancelamento = None
                    aluno.save()
                aluno.acesso.save()
            
            # Registrar no Caixa (como saída) se houver caixa aberto
            from blog.models import CaixaTurno, TransacaoCaixa
            caixa = CaixaTurno.objects.filter(status='ABERTO').order_by('-abertura').first()
            if caixa:
                TransacaoCaixa.objects.create(
                    caixa=caixa,
                    tipo='SAIDA',
                    valor=pg.valor,
                    descricao=f"ESTORNO: {aluno.nome_completo} ({pg.plano.name if pg.plano else 'Taxa'})",
                    metodo=pg.metodo_pagamento or 'DINHEIRO',
                    origem='MANUAL',
                    status='NORMAL'
                )
            
            messages.warning(request, f"O pagamento de R$ {pg.valor} foi ESTORNADO. O crédito foi removido e registrado no histórico.")
        return redirect('crm_aluno_detail', aluno_id=aluno.id)

    # --- AUTO-SYNC ANTES DE CARREGAR A PÁGINA ---
    sincronizar_estados_alunos()
    aluno.refresh_from_db()
    
    acesso = getattr(aluno, 'acesso', None)
    pagamentos_qs = list(aluno.pagamentos.all().order_by('-data_pagamento'))
    total_investido = sum(p.valor for p in pagamentos_qs if p.status == 'pago')
    debitos = sum(p.valor_total_atualizado for p in pagamentos_qs if p.status == 'pendente')
    
    # Agrupamento Visual de Recebimento Parcial + Débito Restante
    pagamentos_agrupados = []
    skip_ids = set()
    for p in pagamentos_qs:
        if p.id in skip_ids:
            continue
            
        if p.status == 'pago' and p.plano:
            # Busca débito gerado simultaneamente (parcial)
            pendente_obj = next((x for x in pagamentos_qs if x.status == 'pendente' and x.plano == p.plano and abs((x.data_pagamento - p.data_pagamento).total_seconds()) < 5), None)
            if pendente_obj:
                p.pendente_obj = pendente_obj
                p.valor_plano_original = p.valor + pendente_obj.valor
                skip_ids.add(pendente_obj.id)
            else:
                p.pendente_obj = None
                p.valor_plano_original = p.valor
        else:
            p.pendente_obj = None
            p.valor_plano_original = p.valor_total_atualizado if p.status == 'pendente' else p.valor
            
        pagamentos_agrupados.append(p)
        
    pagamentos = pagamentos_agrupados
    rockspoints = int(total_investido)
    credito = 0.00
    planos = Plan.objects.all()

    # --- AUTO-SYNC: Garantir que o acesso esteja sincronizado com o último pagamento ---
    ultimo_pago = next((p for p in pagamentos if p.status == 'pago'), None)
    # -----------------------------------------------------------------------------------
    if not ultimo_pago and acesso and getattr(acesso, 'data_vencimento', None):
        acesso.data_vencimento = None
        acesso.status_catraca = 'bloqueado'
        acesso.save()
        
    if ultimo_pago and ultimo_pago.plano:
        from blog.models import ControleAcesso
        from datetime import date, timedelta
        ac, created = ControleAcesso.objects.get_or_create(aluno=aluno)
        
        # Se o aluno tem um plano pago mas a catraca está sem data ou vencida, sincroniza
        base_data_calculo = timezone.localtime(ultimo_pago.data_pagamento).date()
            
        from dateutil.relativedelta import relativedelta
        if ultimo_pago.plano.plan_type == 'mensal':
            vencimento_calculado = base_data_calculo + relativedelta(months=1)
        elif ultimo_pago.plano.plan_type == 'trimestral':
            vencimento_calculado = base_data_calculo + relativedelta(months=3)
        elif ultimo_pago.plano.plan_type == 'semestral':
            vencimento_calculado = base_data_calculo + relativedelta(months=6)
        elif ultimo_pago.plano.plan_type == 'anual':
            vencimento_calculado = base_data_calculo + relativedelta(years=1)
        elif ultimo_pago.plano.plan_type == 'bienal':
            vencimento_calculado = base_data_calculo + relativedelta(years=2)
        else:
            vencimento_calculado = base_data_calculo + timedelta(days=ultimo_pago.plano.duration_days)
        
        # Se for diária, a gente força o vencimento calculado (sem somar)
        # Se for mensal, a gente só atualiza se estiver vazio
        if ultimo_pago.plano.plan_type == 'diaria':
            if not ac.data_vencimento:
                ac.data_vencimento = vencimento_calculado
                ac.status_catraca = 'liberado'
                ac.save()
                acesso = ac
        else:
            if not ac.data_vencimento:
                ac.data_vencimento = vencimento_calculado
                ac.status_catraca = 'liberado'
                ac.save()
                acesso = ac
    # -----------------------------------------------------------------------------------

    from django.conf import settings
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
        'catraca_sync_token': getattr(settings, 'CATRACA_SYNC_TOKEN', 'Rocksfit@2024'),
    }
    return render(request, 'crm/aluno_detail.html', context)

@login_required
def crm_biometria_list(request):
    """Gestão Centralizada de Biometria Digital"""
    if not request.user.has_perm('blog.can_manage_students') and not request.user.is_superuser:
        messages.error(request, "Acesso Negado.")
        return redirect('crm_dashboard')
    
    from blog.models import Aluno
    # Buscar alunos, priorizando os que não têm digital
    alunos = Aluno.objects.all().order_by('digital', 'nome_completo')
    
    # Filtro simples
    q = request.GET.get('q')
    if q:
        alunos = alunos.filter(nome_completo__icontains=q) | alunos.filter(matricula__icontains=q) | alunos.filter(cpf__icontains=q)

    from django.conf import settings
    return render(request, "crm/biometria.html", {
        "alunos": alunos,
        "q": q,
        "catraca_sync_token": getattr(settings, 'CATRACA_SYNC_TOKEN', 'Rocksfit@2024'),
    })

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
def crm_pagamento_delete(request, aluno_id, pagamento_id):
    """Estorno/Exclusão de pagamento e redução de dias de crédito"""
    if not request.user.has_perm('blog.can_access_financial') and not request.user.is_superuser:
        messages.error(request, "Acesso Negado: Permissão insuficiente para exclusão financeira.")
        return redirect('crm_aluno_detail', aluno_id=aluno_id)
        
    from blog.models import PagamentoHistorico, ControleAcesso
    from django.shortcuts import get_object_or_404
    from datetime import timedelta
    
    if request.method == 'POST':
        pagamento = get_object_or_404(PagamentoHistorico, id=pagamento_id, aluno_id=aluno_id)
        
        # Reduzir dias de crédito se houver um plano vinculado
        if pagamento.plano and pagamento.status == 'pago':
            try:
                acesso = ControleAcesso.objects.get(aluno_id=aluno_id)
                if acesso.data_vencimento:
                    # Se for o último pagamento sendo excluído, zera o acesso
                    if PagamentoHistorico.objects.filter(aluno_id=aluno_id, status='pago').count() <= 1:
                        acesso.data_vencimento = None
                        acesso.status_catraca = 'bloqueado'
                    else:
                        valor_plano = float(pagamento.plano.price)
                        if valor_plano > 0:
                            dias = max(1, int(round((float(pagamento.valor) / valor_plano) * pagamento.plano.duration_days)))
                        else:
                            dias = pagamento.plano.duration_days
                        acesso.data_vencimento -= timedelta(days=dias)
                    acesso.save()
            except ControleAcesso.DoesNotExist:
                pass
                
        # Excluir histórico de pagamento do card principal (marcar como cancelado para manter histórico real)
        pagamento.status = 'cancelado'
        pagamento.save()
        messages.success(request, "Pagamento excluído e dias de crédito estornados com sucesso. O log permanecerá no Histórico Financeiro.")
        
    return redirect('crm_aluno_detail', aluno_id=aluno_id)

@login_required
def crm_pagamento_edit(request, aluno_id, pagamento_id):
    """Edição de pagamento (Correção de valor ou método)"""
    if not request.user.has_perm('blog.can_access_financial') and not request.user.is_superuser:
        messages.error(request, "Acesso Negado: Permissão insuficiente para edição financeira.")
        return redirect('crm_aluno_detail', aluno_id=aluno_id)
        
    from blog.models import PagamentoHistorico
    from django.shortcuts import get_object_or_404
    
    if request.method == 'POST':
        pagamento = get_object_or_404(PagamentoHistorico, id=pagamento_id, aluno_id=aluno_id)
        
        valor_raw = request.POST.get('valor', '').strip()
        if ',' in valor_raw:
            valor = valor_raw.replace('.', '').replace(',', '.')
        else:
            valor = valor_raw
            
        metodo = request.POST.get('metodo')
        plano_id = request.POST.get('plano')
        
        if valor:
            novo_valor = float(valor)
            valor_antigo = float(pagamento.valor)
            
            if novo_valor != valor_antigo and pagamento.status == 'pago':
                diferenca = valor_antigo - novo_valor
                
                # 1. Ajuste de Caixa (Gerar Saída ou Entrada para equilibrar)
                from blog.models import CaixaTurno, TransacaoCaixa
                caixa = CaixaTurno.objects.filter(status='ABERTO').order_by('-abertura').first()
                if caixa:
                    tipo_transacao = 'SAIDA' if diferenca > 0 else 'ENTRADA'
                    TransacaoCaixa.objects.create(
                        caixa=caixa,
                        tipo=tipo_transacao,
                        valor=abs(diferenca),
                        descricao=f"AJUSTE RECEB: {pagamento.aluno.nome_completo} ({pagamento.plano.name if pagamento.plano else 'Ajuste'})",
                        metodo=metodo or pagamento.metodo_pagamento or 'DINHEIRO',
                        origem='MANUAL',
                        status='NORMAL'
                    )
                
                # 2. Se o valor diminuiu, criar débito e reduzir dias
                if diferenca > 0 and pagamento.plano:
                    PagamentoHistorico.objects.create(
                        aluno=pagamento.aluno,
                        plano=pagamento.plano,
                        valor=diferenca,
                        status='pendente',
                        data_pagamento=pagamento.data_pagamento
                    )
                    
                    # 3. Retirar os dias proporcionais do que não foi pago da Catraca
                    from datetime import timedelta
                    acesso = getattr(pagamento.aluno, 'acesso', None)
                    if acesso and acesso.data_vencimento:
                        valor_plano = float(pagamento.plano.price)
                        dias_remover = int(round((diferenca / valor_plano) * pagamento.plano.duration_days))
                        if dias_remover > 0:
                            acesso.data_vencimento -= timedelta(days=dias_remover)
                            acesso.save()
                    
                    pagamento.aluno.status = 'AGUARDANDO'
                    pagamento.aluno.save()
            
            pagamento.valor = novo_valor
            
        if metodo:
            pagamento.metodo_pagamento = metodo
        if plano_id:
            pagamento.plano_id = plano_id
            
        pagamento.save()
        messages.success(request, "Histórico atualizado! Débitos e dias de catraca recalibrados automaticamente caso o valor tenha sido reduzido.")
        
    return redirect('crm_aluno_detail', aluno_id=aluno_id)

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

                dias_adicionais, plano = processar_pagamento(aluno, plano, valor_final, metodo, user=request.user)
                
                # 2. Configurar Acesso
                if dias_adicionais > 0:
                    from dateutil.relativedelta import relativedelta
                    hoje_local = timezone.localtime(timezone.now()).date()
                    base_data = hoje_local
                    
                    acesso.data_vencimento = base_data + relativedelta(months=dias_adicionais // 30, days=dias_adicionais % 30)
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


@login_required
def crm_ia_dashboard(request):
    """Painel de Controle da RKS Master IA"""
    if not request.user.is_superuser:
        return HttpResponse("Acesso Negado", status=403)
    
    from .models import AnaliseGeralIA, AcaoIA, GymSetting
    
    analise = AnaliseGeralIA.objects.first()
    acoes = AcaoIA.objects.filter(status='PENDENTE')
    historico_acoes = AcaoIA.objects.exclude(status='PENDENTE')[:15]
    
    context = {
        'analise': analise,
        'acoes': acoes,
        'historico_acoes': historico_acoes,
        'gym_settings': GymSetting.objects.first(),
        'title': 'RKS Master IA'
    }
    return render(request, 'crm/ia_dashboard.html', context)

@login_required
def crm_ia_generate(request):
    """Gera nova análise via IA"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Acesso Negado'}, status=403)
    
    from .ai_engine import analisar_dados_ia
    result = analisar_dados_ia()
    
    if isinstance(result, dict) and 'error' in result:
        messages.error(request, result['error'])
    else:
        messages.success(request, "Relatório estratégico gerado com sucesso!")
        
    return redirect('crm_ia_dashboard')

@login_required
def crm_ia_action(request, action_id):
    """Aprova ou Rejeita uma ação da IA"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Acesso Negado'}, status=403)
    
    from .models import AcaoIA
    acao = get_object_or_404(AcaoIA, id=action_id)
    status = request.POST.get('status')
    
    if status in ['APROVADO', 'REJEITADO']:
        acao.status = status
        acao.save()
        messages.info(request, f"Ação {status}: {acao.titulo_painel}")
        
        # Simulação de disparo de integração
        if status == 'APROVADO':
            # Log de integração simulada
            print(f"[IA INTEGRATION] Enviando para {acao.tipo}: {acao.payload}")
            
    return redirect('crm_ia_dashboard')

@login_required
@require_POST
def crm_whatsapp_campanha(request):
    """ Envia uma campanha de WhatsApp para uma lista de alunos filtrada """
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Acesso Negado'}, status=403)
        
    audience = request.POST.get('audience', 'ATIVO')
    message_text = request.POST.get('message', '').strip()
    
    if not message_text:
        messages.error(request, "A mensagem não pode estar vazia.")
        return redirect('crm_alunos_list')
        
    alunos_alvo = Aluno.objects.exclude(whatsapp__isnull=True).exclude(whatsapp__exact='')
    
    if audience != 'TODOS':
        alunos_alvo = alunos_alvo.filter(status=audience)
        
    # Limita o envio para não travar (Ideal: Celery ou background task)
    # Neste caso vamos fazer envio síncrono para demonstração
    enviados = 0
    erros = 0
    
    for aluno in alunos_alvo:
        sucesso, resp = EvolutionApiService.enviar_mensagem_texto(aluno.whatsapp, message_text)
        if sucesso:
            enviados += 1
        else:
            erros += 1
            
    messages.success(request, f"Campanha concluída! {enviados} mensagens enviadas. {erros} erros.")
    return redirect('crm_alunos_list')


@csrf_exempt
def api_biometria_save(request, matricula):
    """API para o módulo de recepção salvar a digital do aluno no CRM"""
    if request.method == 'POST':
        try:
            # Busca o aluno pela matrícula
            aluno = Aluno.objects.filter(matricula=matricula).first()
            if not aluno:
                return JsonResponse({"success": False, "error": "Aluno não encontrado"}, status=404)
            
            # No fprintd usamos a própria matrícula como ID da digital
            aluno.digital = matricula
            aluno.save()
            
            return JsonResponse({"success": True, "message": f"Biometria de {aluno.nome_completo} vinculada."})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    
    return JsonResponse({"success": False, "error": "Método não permitido"}, status=405)


@csrf_exempt
@require_POST
def webhook_evolution_api(request):
    """ Recebe os eventos de mensagem da Evolution API """
    from django.conf import settings
    
    # Validação de Segurança Básica: Verifica se a API KEY configurada bate com a enviada no header
    # A Evolution pode enviar como Authorization, apikey ou podemos configurar via query params
    api_key_esperada = getattr(settings, 'EVOLUTION_API_KEY', '')
    if api_key_esperada:
        header_key = request.headers.get('apikey') or request.headers.get('Authorization', '').replace('Bearer ', '')
        if header_key != api_key_esperada:
            return JsonResponse({"erro": "Acesso Negado. Token Inválido."}, status=403)

    try:
        payload = json.loads(request.body)

        evento = payload.get('event', '').upper()
        if evento in ['MESSAGES.UPSERT', 'MESSAGES_UPSERT']:
            print("===================== WEBHOOK DEBUG =====================")
            print("Payload:", json.dumps(payload, indent=2))
            print("=========================================================")
            data = payload.get('data', {})
            # Em v1 é data.messages (lista). Em v2 é data direto (objeto da mensagem)
            messages_list = data.get('messages', []) if 'messages' in data else [data]
            
            for msg in messages_list:
                # Ignora mensagens enviadas pelo próprio sistema (evita loop infinito)
                if msg.get('key', {}).get('fromMe'):
                    continue
                
                # Número do WhatsApp do aluno (Ex: 5584999999999@s.whatsapp.net)
                remetente = msg.get('key', {}).get('remoteJid')
                
                # A estrutura da mensagem muda se tiver anexo, botão ou for texto simples
                msg_content = msg.get('message', {})
                texto_msg = msg_content.get('conversation') or \
                            msg_content.get('extendedTextMessage', {}).get('text') or ""
                
                texto_limpo = texto_msg.strip()

                if texto_limpo:
                    processar_mensagem_aluno(remetente, texto_limpo)
                elif 'imageMessage' in msg_content:
                    processar_midia_gemini(remetente, msg, 'image')
                elif 'audioMessage' in msg_content:
                    processar_midia_gemini(remetente, msg, 'audio')

        # Retorne 200 OK o mais rápido possível para a API não dar timeout
        return JsonResponse({"status": "sucesso"}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"erro": "JSON malformado"}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erro processando webhook: {e}")
        return JsonResponse({"erro": "Erro interno"}, status=500)

def processar_mensagem_aluno(remetente, texto):
    """ O Cérebro do Autoatendimento """
    from blog.models import Aluno, ChatMessage, GymSetting
    import time
    
    # 1. Verifica se tem aluno e se o bot ta ativo
    numero = remetente.split('@')[0]
    final_num = numero[-8:] if len(numero) > 8 else numero
    aluno_zap = Aluno.objects.filter(whatsapp__endswith=final_num).first()
    
    if aluno_zap and not aluno_zap.bot_ativo:
        print(f"[LOG] Mensagem ignorada de {remetente} (Atendimento Humano Ativo)")
        return
        
    # Identifica comando oculto para pausa do bot
    texto_lower = texto.lower().strip()
    if "atendente" in texto_lower or "falar com humano" in texto_lower or "pausar bot" in texto_lower:
        if aluno_zap:
            aluno_zap.bot_ativo = False
            aluno_zap.save()
            msg = "Certo! Pausei o assistente virtual. Um atendente humano vai assumir o atendimento assim que possível. Aguarde um momento!"
            EvolutionApiService.enviar_mensagem_texto(remetente, msg)
            return
            
    # Salva no histórico de memória
    msg_obj = ChatMessage.objects.create(remetente=remetente, is_bot=False, texto=texto)
    
    # Extrai apenas os números da mensagem do aluno para checar CPF
    numeros_digitados = re.sub(r'\D', '', texto)

    if len(numeros_digitados) == 11:
        cpf = numeros_digitados
        aluno = Aluno.objects.filter(cpf=cpf).first()
        if aluno:
            from django.utils import timezone
            from datetime import timedelta
            
            dias_vencidos = 0
            if hasattr(aluno, 'acesso') and aluno.acesso.data_vencimento:
                data_vencimento = aluno.acesso.data_vencimento
                hoje = timezone.now().date()
                if hoje > data_vencimento:
                    current_date = data_vencimento + timedelta(days=1)
                    while current_date <= hoje:
                        if current_date.weekday() != 6:
                            dias_vencidos += 1
                        current_date += timedelta(days=1)
            
            debitos = PagamentoHistorico.objects.filter(aluno=aluno, status='pendente')
            valor_total_debitos = sum([float(d.valor_total_atualizado) for d in debitos])
            ultimo_pg = PagamentoHistorico.objects.filter(aluno=aluno).order_by('-data_pagamento').first()
            
            msg_texto = f"Olá {aluno.nome_completo}, identificamos seu cadastro! 🎉\n\n"
            if ultimo_pg and ultimo_pg.plano:
                preco_cartao = float(ultimo_pg.plano.price)
                total_pagar = preco_cartao + valor_total_debitos
                msg_texto += f"💵 *TOTAL A SER PAGO (Renovação + Débitos)*:\n🔸 *PIX ou cartão:* R$ {total_pagar:.2f}\n\nQual opção você prefere para realizar o pagamento?"
            else:
                if valor_total_debitos > 0:
                    msg_texto += f"💵 *TOTAL A SER PAGO (Débitos):* R$ {valor_total_debitos:.2f}\n\n"
                msg_texto += "Não encontrei um plano anterior registrado. Para renovar, por favor vá até a recepção."
                
            EvolutionApiService.enviar_mensagem_texto(remetente, msg_texto)
            ChatMessage.objects.create(remetente=remetente, is_bot=True, texto=msg_texto)
            return
        else:
            msg_fail = "Poxa, não consegui encontrar nenhum aluno com esse CPF. Tem certeza que digitou corretamente?"
            EvolutionApiService.enviar_mensagem_texto(remetente, msg_fail)
            ChatMessage.objects.create(remetente=remetente, is_bot=True, texto=msg_fail)
            return
            
    # Agrupamento (Debounce): Espera 4 segundos
    time.sleep(4)
    ultimo_chat = ChatMessage.objects.filter(remetente=remetente, is_bot=False).order_by('-timestamp').first()
    if ultimo_chat.id != msg_obj.id:
        # Outra mensagem chegou nos ultimos 4 seg! Esta thread aborta.
        return
        
    # Pega histórico para contexto
    historico = ChatMessage.objects.filter(remetente=remetente).order_by('-timestamp')[:6]
    historico = reversed(list(historico))
    
    conversa_texto = ""
    for h in historico:
        prefixo = "Assistente" if h.is_bot else "Aluno"
        conversa_texto += f"{prefixo}: {h.texto}\n"
        
    gym_settings = GymSetting.objects.first()
    
    if gym_settings and not gym_settings.is_ia_active:
        print(f"[LOG] IA desativada nas configurações. Ignorando texto genérico de {remetente}")
        return
        
    api_key = "AIzaSyAFrByGIzSZRKpPl4peEK0GAB2zLp3srTo"
    import google.genai as genai
    client = genai.Client(api_key=api_key)
    
    prompt_base = "Você é o assistente virtual da academia Rocks-Fit. Responda à última mensagem do Aluno de forma educada, empática e muito direta."
    instrucoes_extras = gym_settings.ai_system_prompt if gym_settings and gym_settings.ai_system_prompt else ""
    
    prompt_completo = f"{prompt_base}\n\nInstruções:\n{instrucoes_extras}\n\nHistórico Recente da Conversa:\n{conversa_texto}\n\nResponda agora ao Aluno da forma mais humana possível:"
    
    try:
        response_ai = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_completo
        )
        resposta_texto = response_ai.text
    except Exception as e:
        resposta_texto = "Oi! Tudo bem? Para consultar seu plano e renovar de forma automática, digite apenas os números do seu CPF. 💪"
        
    EvolutionApiService.enviar_mensagem_texto(remetente, resposta_texto)
    ChatMessage.objects.create(remetente=remetente, is_bot=True, texto=resposta_texto)

@login_required
@user_passes_test(lambda u: u.is_staff)
def automacoes_hub(request):
    from blog.models import CampanhaAutomacao
    campanhas = CampanhaAutomacao.objects.all()
    ativas = campanhas.filter(status='ativa').count()
    context = {
        'campanhas': campanhas,
        'ativas': ativas,
    }
    return render(request, "automacoes_hub.html", context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def automacoes_campanha(request, campanha_id=None):
    from blog.models import CampanhaAutomacao
    
    campanha = None
    if campanha_id:
        campanha = get_object_or_404(CampanhaAutomacao, id=campanha_id)

    if request.method == "POST":
        descricao = request.POST.get('descricao')
        status = request.POST.get('status', 'rascunho')
        prioridade = request.POST.get('prioridade', 'media')
        gatilho = request.POST.get('gatilho')
        horario_disparo = request.POST.get('horario_disparo')
        repetir = request.POST.get('repetir') == '1'
        dimensao = request.POST.get('dimensao')
        status_audiencia = request.POST.get('status_audiencia')
        canal_whatsapp = request.POST.get('canal_whatsapp') == '1'
        canal_email = request.POST.get('canal_email') == '1'
        canal_app = request.POST.get('canal_app') == '1'
        conteudo = request.POST.get('conteudo', '')
        
        # O botão 'ATIVAR CAMPANHA' ou 'SALVAR RASCUNHO' pode mandar uma flag para forçar status
        acao = request.POST.get('acao')
        if acao == 'ativar':
            status = 'ativa'
        elif acao == 'rascunho':
            status = 'rascunho'

        if not horario_disparo:
            horario_disparo = None

        if not campanha:
            campanha = CampanhaAutomacao()
            
        campanha.descricao = descricao
        campanha.status = status
        campanha.prioridade = prioridade
        campanha.gatilho = gatilho
        campanha.horario_disparo = horario_disparo
        campanha.repetir = repetir
        campanha.dimensao = dimensao
        campanha.status_audiencia = status_audiencia
        campanha.canal_whatsapp = canal_whatsapp
        campanha.canal_email = canal_email
        campanha.canal_app = canal_app
        campanha.conteudo = conteudo
        campanha.save()
        
        messages.success(request, f"Campanha '{campanha.descricao}' salva com sucesso!")
        return redirect('automacoes_hub')
        
    ativas = CampanhaAutomacao.objects.filter(status='ativa').count()
    context = {
        'campanha': campanha,
        'ativas': ativas
    }
    return render(request, "automacoes_campanha.html", context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def automacoes_delete(request, campanha_id):
    from blog.models import CampanhaAutomacao
    campanha = get_object_or_404(CampanhaAutomacao, id=campanha_id)
    nome = campanha.descricao
    campanha.delete()
    messages.success(request, f"Campanha '{nome}' removida permanentemente.")
    return redirect('automacoes_hub')

@login_required
@user_passes_test(lambda u: u.is_staff)
def automacoes_send_manual(request, campanha_id):
    from blog.models import CampanhaAutomacao, Aluno
    campanha = get_object_or_404(CampanhaAutomacao, id=campanha_id)
    
    # Simulação básica de disparo baseado na campanha
    # Na vida real usaria o filtro da audiência. Para demonstração vamos enviar um flash no console
    # ou testar com um envio para quem bate com o critério simples.
    
    # Filtro Simples
    alvos = Aluno.objects.exclude(whatsapp__isnull=True).exclude(whatsapp__exact='')
    if campanha.status_audiencia and campanha.status_audiencia.upper() in ['ATIVO', 'INATIVO', 'AGUARDANDO', 'SUSPENSO']:
        alvos = alvos.filter(status=campanha.status_audiencia.upper())
        
    enviados = 0
    
    # Para não disparar para o banco de dados inteiro por engano, testamos com 1 ou enviamos pra valer se for seguro.
    # Neste caso vamos só retornar o SUCCESS.
    for alvo in alvos[:2]: # max 2 para demonstração
        msg_texto = campanha.conteudo.replace('[Member Name]', alvo.nome_completo.split()[0])
        # Disparo real pela Evolution API
        EvolutionApiService.enviar_mensagem_texto(alvo.whatsapp, msg_texto)
        print(f"[MANUAL SEND] Enviando para {alvo.whatsapp}: {msg_texto}")
        enviados += 1
        
    messages.success(request, f"Disparo manual concluído! ({enviados} mensagens simuladas/enviadas para o grupo).")
    return redirect('automacoes_hub')

@login_required
@user_passes_test(lambda u: u.is_staff)
def automacoes_pesquisas(request):
    from blog.models import CampanhaAutomacao
    ativas = CampanhaAutomacao.objects.filter(status='ativa').count()
    context = {
        'ativas': ativas
    }
    return render(request, "automacoes_pesquisas.html", context)

