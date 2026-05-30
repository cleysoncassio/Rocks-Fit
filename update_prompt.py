import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings.development")
django.setup()

from blog.models import GymSetting, ContactInfo, Program, Schedule, Trainer, Plan

contact = ContactInfo.objects.first()
programs = Program.objects.all()
schedules = Schedule.objects.all()
trainers = Trainer.objects.all()
plans = Plan.objects.all()

prompt = "Você é a inteligência artificial de atendimento da academia Rocks-Fit.\n\n"
prompt += "INFORMAÇÕES DA ACADEMIA ROCKS-FIT:\n\n"

if contact:
    prompt += f"LOCALIZAÇÃO E CONTATO:\nEndereço: {contact.address}\nTelefone: {contact.phone}\nE-mail: {contact.email}\nSite: {contact.website}\n\n"

prompt += "PLANOS OFERECIDOS:\n"
for p in plans:
    prompt += f"- {p.name}: R$ {p.price} (Tipo: {p.plan_type}). {p.description}\n"

prompt += "\nMODALIDADES / PROGRAMAS:\n"
for p in programs:
    prompt += f"- {p.name}: {p.description}\n"

prompt += "\nHORÁRIOS DE AULAS ESPECÍFICAS:\n"
for s in schedules:
    prog_name = s.program.name if s.program else "Geral"
    tr_name = s.trainer.name if s.trainer else "Sem prof. definido"
    prompt += f"- {s.get_day_display()} ({s.get_shift_display()}): {s.start_time.strftime('%H:%M')} as {s.end_time.strftime('%H:%M')} - {prog_name} com {tr_name}\n"

prompt += "\nPROFESSORES:\n"
for t in trainers:
    prompt += f"- {t.name}: {t.title}. {t.description}\n"

prompt += "\n\nDIRETRIZES GERAIS DE COMPORTAMENTO:\n"
prompt += "1. Seja extremamente educado, amigável e demonstre entusiasmo (use emojis moderadamente).\n"
prompt += "2. O cliente envia áudios curtos ou mensagens curtas pelo WhatsApp, então suas respostas também devem ser curtas e ir direto ao ponto.\n"
prompt += "3. Baseie-se APENAS nas informações fornecidas acima. Se o aluno perguntar algo que não está nessa lista, diga que não tem essa informação no momento e que ele pode verificar na recepção.\n"
prompt += "4. Se o aluno mandar um comprovante, confirme que recebeu e que a recepção fará a liberação, mas interaja de acordo com as perguntas que ele fizer.\n"

gs = GymSetting.objects.first()
if gs:
    gs.ai_system_prompt = prompt
    gs.save()
    print("Prompt atualizado com sucesso!")
else:
    print("Nenhuma configuracao da academia encontrada no banco.")
