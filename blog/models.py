from django.contrib.auth.models import AbstractUser
from django.db import models
from ordered_model.models import OrderedModel


class User(AbstractUser):
    # Campos adicionais para o seu modelo de User personalizado
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=30, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to="user_avatars/", null=True, blank=True)
    website = models.URLField(max_length=100, blank=True)

    # Se você quiser adicionar campos aos grupos e permissões para evitar conflitos
    groups = models.ManyToManyField(
        "auth.Group",
        verbose_name="groups",
        blank=True,
        related_name="blog_users",
        related_query_name="blog_user",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        verbose_name="user permissions",
        blank=True,
        related_name="blog_users",
        related_query_name="blog_user",
    )

    def __str__(self):
        return self.username


class Program(OrderedModel):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to="program_images/", blank=True, null=True)
    icon = models.ImageField(
        upload_to="program_icons/",
        blank=True,
        null=True,
        verbose_name="Ícone da Modalidade",
        help_text="Envie um ícone (PNG/SVG) para representar esta modalidade nos horários e cards."
    )
    join_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta(OrderedModel.Meta):
        verbose_name = "Modalidade"
        verbose_name_plural = "05. Academia: Modalidades"


class Trainer(models.Model):
    name = models.CharField(max_length=100)
    title = models.CharField(
        max_length=100, blank=True, null=True
    )  # Para o título como "Professor"
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="trainer_images/", blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Professor"
        verbose_name_plural = "06. Academia: Professores"


class Schedule(models.Model):
    DAY_CHOICES = [
        ("monday", "Segunda-feira"),
        ("tuesday", "Terça-feira"),
        ("wednesday", "Quarta-feira"),
        ("thursday", "Quinta-feira"),
        ("friday", "Sexta-feira"),
        ("saturday", "Sábado"),
        ("sunday", "Domingo"),
    ]

    SHIFT_CHOICES = [
        ("manha", "Manhã"),
        ("meio_dia", "Meio-dia"),
        ("tarde", "Tarde"),
        ("noite", "Noite"),
    ]

    day = models.CharField(max_length=10, choices=DAY_CHOICES, verbose_name="Dia da Semana")
    shift = models.CharField(max_length=20, choices=SHIFT_CHOICES, default="manha", verbose_name="Turno")
    start_time = models.TimeField(verbose_name="Início")
    end_time = models.TimeField(verbose_name="Fim")
    program = models.ForeignKey(Program, on_delete=models.CASCADE, verbose_name="Modalidade")
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE, verbose_name="Professor")

    def __str__(self):
        return f"{self.get_day_display()} - {self.get_shift_display()} ({self.trainer.name})"

    class Meta:
        verbose_name = "Horário de Funcionamento"
        verbose_name_plural = "07. Academia: Horários de Funcionamento"
        ordering = ['day', 'start_time']


class ContactInfo(models.Model):
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.address


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} at {self.created_at}"



class Plan(OrderedModel):
    PLAN_TYPE_CHOICES = [
        ('diaria', 'Diária'),
        ('mensal', 'Mensal'),
        ('trimestral', 'Trimestral'),
    ]
    name = models.CharField(max_length=100, verbose_name="Nome do Plano")
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES, default='mensal', verbose_name="Tipo de Vencimento")
    duration_days = models.IntegerField(default=30, verbose_name="Dias de Acesso", help_text="Quantos dias de acesso liberar na catraca após o pagamento.")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço")
    period = models.CharField(max_length=50, verbose_name="Período (ex: /mensal)")
    description = models.TextField(verbose_name="Descrição Curta")
    is_popular = models.BooleanField(default=False, verbose_name="Mais Vendido?")
    features = models.TextField(verbose_name="Benefícios", help_text="Insira cada benefício em uma nova linha.")
    card_button_text = models.CharField(max_length=50, blank=True, null=True, verbose_name="Texto do Botão no Card", help_text="Texto exibido no botão do card de planos (ex: 'Assinar Agora'). Padrão: Assinar Agora")
    button1_text = models.CharField(max_length=100, blank=True, null=True, verbose_name="Texto do Botão InfinitePay (Checkout)", help_text="Texto do botão de pagamento via cartão na página de checkout.")
    button1_url = models.URLField(blank=True, null=True, verbose_name="Link do Botão 1")
    button2_text = models.CharField(max_length=100, blank=True, null=True, verbose_name="Texto do Botão PIX (Checkout)", help_text="Texto do botão de pagamento via PIX na página de checkout.")
    button2_url = models.URLField(blank=True, null=True, verbose_name="Link do Botão 2")
    infinitepay_link = models.URLField(blank=True, null=True, verbose_name="Link InfinitePay (Checkout)", help_text="Link específico de pagamento deste plano na InfinitePay (ex: https://invoice.infinitepay.io/plans/rocks-fit/...)")

    @property
    def get_features_list(self):
        return [feature.strip() for feature in self.features.split('\n') if feature.strip()]

    def __str__(self):
        return self.name

    class Meta(OrderedModel.Meta):
        verbose_name = "Plano e Pacote"
        verbose_name_plural = "03. Gestão: Planos e Pacotes"

import datetime

class Aluno(models.Model):
    matricula = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="Matrícula")
    nome_completo = models.CharField(max_length=200, verbose_name="Nome Completo")
    cpf = models.CharField(max_length=14, unique=True, verbose_name="CPF")
    data_nascimento = models.DateField(blank=True, null=True, verbose_name="Data de Nascimento")
    email = models.EmailField(verbose_name="E-mail")
    whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp")
    foto = models.ImageField(upload_to="alunos/fotos/", blank=True, null=True, verbose_name="Foto (Reconhecimento Facial)")
    digital = models.TextField(blank=True, null=True, verbose_name="Digital (Template Biométrico)")
    data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name="Data de Cadastro")

    def save(self, *args, **kwargs):
        if not self.matricula:
            # Geração automática: RF + Ano + Sequencial
            ano_atual = datetime.datetime.now().year
            prefixo = f"RF{ano_atual}"
            
            # Buscar a maior matrícula do ano atual
            ultimo_aluno = Aluno.objects.filter(matricula__startswith=prefixo).order_by('-matricula').first()
            
            if ultimo_aluno and ultimo_aluno.matricula:
                try:
                    # Tenta extrair o número da última matrícula e somar 1
                    ultimo_numero = int(ultimo_aluno.matricula[len(prefixo):])
                    proximo_numero = ultimo_numero + 1
                except (ValueError, IndexError):
                    proximo_numero = 1
            else:
                proximo_numero = 1
                
            self.matricula = f"{prefixo}{proximo_numero:04d}"
            
            # Garantir unicidade final em caso de corrida
            while Aluno.objects.filter(matricula=self.matricula).exists():
                proximo_numero += 1
                self.matricula = f"{prefixo}{proximo_numero:04d}"

        super().save(*args, **kwargs)

    @property
    def tempo_permanencia(self):
        """ Retorna quantos dias o aluno está cadastrado na academia """
        from django.utils import timezone
        diff = timezone.now() - self.data_cadastro
        return f"{diff.days} dias"

    def __str__(self):
        return f"{self.matricula} - {self.nome_completo}"

    class Meta:
        verbose_name = "Aluno para Matrícula"
        verbose_name_plural = "01. Gestão: Alunos para Matrícula"

class PagamentoHistorico(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('pago', 'Pago'),
        ('recusado', 'Recusado'),
    ]
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='pagamentos', verbose_name="Aluno")
    plano = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, verbose_name="Plano")
    transacao_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID da Transação (Referência)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente', verbose_name="Status")
    metodo_pagamento = models.CharField(max_length=50, blank=True, null=True, verbose_name="Método (Pix/Cartão)")
    data_pagamento = models.DateTimeField(auto_now_add=True, verbose_name="Data")

    def __str__(self):
        return f"Pagamento {self.id} - {self.aluno} - {self.status}"

    class Meta:
        verbose_name = "Histórico de Pagamento"
        verbose_name_plural = "02. Gestão: Histórico de Pagamentos"

class ControleAcesso(models.Model):
    STATUS_CATRACA_CHOICES = [
        ('liberado', 'Liberado'),
        ('aguardando_biometria', 'Aguardando Biometria (Pago)'),
        ('aguardando_pagamento', 'Aguardando Confirmação de Pagamento (PIX)'),
        ('bloqueado', 'Bloqueado'),
    ]
    aluno = models.OneToOneField(Aluno, on_delete=models.CASCADE, related_name='acesso', verbose_name="Aluno")
    data_vencimento = models.DateField(blank=True, null=True, verbose_name="Data de Vencimento")
    status_catraca = models.CharField(max_length=25, choices=STATUS_CATRACA_CHOICES, default='bloqueado', verbose_name="Status na Catraca")
    abrir_catraca_agora = models.BooleanField(default=False, verbose_name="Liberar Catraca Agora?")
    plano_pendente = models.ForeignKey(
        'Plan', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='acessos_pendentes',
        verbose_name="Plano Aguardando 1ª Entrada",
        help_text="Plano pago, aguardando biometria para ativar e calcular vencimento."
    )

    def __str__(self):
        return f"Acesso {self.aluno.nome_completo} - {self.status_catraca}"

    class Meta:
        verbose_name = "Controle de Acesso"
        verbose_name_plural = "04. Gestão: Controle de Acesso"


class SiteConfiguration(models.Model):
    # Hero/Header
    hero_image = models.ImageField(upload_to='site_images/', blank=True, null=True, verbose_name="Imagem do Cabeçalho (Hero)")
    hero_title = models.CharField(max_length=200, blank=True, null=True, verbose_name="Título do Hero")
    hero_subtitle = models.CharField(max_length=300, blank=True, null=True, verbose_name="Subtítulo do Hero")

    # Parallax backgrounds
    pricing_background = models.ImageField(upload_to='site_images/', blank=True, null=True, verbose_name="Fundo Parallax: Planos")
    ps_parallax_background = models.ImageField(upload_to='site_images/', blank=True, null=True, verbose_name="Fundo Parallax: PS (Rodapé Intro)")
    contact_background = models.ImageField(upload_to='site_images/', blank=True, null=True, verbose_name="Fundo Parallax: Contato")
    about_background = models.ImageField(upload_to='site_images/', blank=True, null=True, verbose_name="Fundo Parallax: Sobre Nós")
    programs_background = models.ImageField(upload_to='site_images/', blank=True, null=True, verbose_name="Fundo Parallax: Modalidades")
    trainers_background = models.ImageField(upload_to='site_images/', blank=True, null=True, verbose_name="Fundo Parallax: Professores")
    schedule_background = models.ImageField(upload_to='site_images/', blank=True, null=True, verbose_name="Fundo Parallax: Cronograma")

    # Logos
    intro_logo = models.ImageField(upload_to='site_images/', blank=True, null=True, verbose_name="Logo da Introdução")
    footer_logo = models.ImageField(upload_to='site_images/', blank=True, null=True, verbose_name="Logo do Rodapé")

    def __str__(self):
        return "Fotos do Site"

    class Meta:
        verbose_name = "Design: Fotos do Site"
        verbose_name_plural = "00. Design: Fotos do Site"

# --- 🚀 SINCRONIZAÇÃO LOCAL (rks-catraca) ---
from django.db.models.signals import post_save
from django.dispatch import receiver
import json
import os

@receiver(post_save, sender=Aluno)
def exportar_alunos_json(sender, instance, **kwargs):
    """ Gera um cache local em JSON para o Gestor de Alunos """
    try:
        from blog.models import Aluno
        alunos = Aluno.objects.all().select_related('acesso')
        lista = []
        for a in alunos:
            status = "INATIVO"
            vencimento = "SEM PLANO"
            if hasattr(a, 'acesso'):
                status = a.acesso.status_catraca.upper()
                venc = a.acesso.data_vencimento
                vencimento = venc.strftime('%d/%m/%Y') if venc else "SEM VENCIMENTO"
            
            lista.append({
                'id': a.id,
                'nome': a.nome_completo,
                'matricula': a.matricula,
                'cpf': a.cpf,
                'status': status,
                'vencimento': vencimento,
                'foto_url': a.foto.url if a.foto else None,
                'tem_foto': bool(a.foto),
                'tem_digital': bool(a.digital)
            })
        
        caminho = "/home/ccs/Modelos/Rocks-Fit/rks-catraca/alunos_local.json"
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump({'alunos': lista}, f, ensure_ascii=False, indent=4)
        print(f"[SYNC] Arquivo local atualizado: {len(lista)} alunos.")
    except Exception as e:
        print(f"[SYNC] Erro ao gerar cache local: {e}")

# Também disparar quando o Controle de Acesso mudar (vencimento, etc)
from django.db.models.signals import post_save
from .models import ControleAcesso
@receiver(post_save, sender=ControleAcesso)
def exportar_pelo_acesso(sender, instance, **kwargs):
    exportar_alunos_json(sender=Aluno, instance=None)
