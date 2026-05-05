from django.contrib.auth.models import AbstractUser
from django.db import models
from ordered_model.models import OrderedModel


class User(AbstractUser):
    TYPE_SUPERADMIN = 'superadmin'
    TYPE_ADMIN = 'admin'
    TYPE_SECRETARY = 'secretary'
    TYPE_TRAINER = 'trainer'
    TYPE_NUTRITIONIST = 'nutritionist'
    TYPE_STUDENT = 'student'

    USER_TYPE_CHOICES = (
        (TYPE_SUPERADMIN, 'SuperAdmin'),
        (TYPE_ADMIN, 'Administrador'),
        (TYPE_SECRETARY, 'Secretário(a)'),
        (TYPE_TRAINER, 'Professor(a)'),
        (TYPE_NUTRITIONIST, 'Nutricionista'),
        (TYPE_STUDENT, 'Aluno(a)'),
    )

    email = models.EmailField(unique=True, verbose_name="E-mail")
    cpf = models.CharField(max_length=14, unique=True, db_index=True, null=True, blank=True, verbose_name="CPF")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefone")
    avatar = models.ImageField(upload_to="user_avatars/", null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="Data de Nascimento")
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default=TYPE_STUDENT, verbose_name="Tipo de Usuário")
    
    is_2fa_enabled = models.BooleanField(default=False, verbose_name="2FA Ativado")
    last_login_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="Último IP")
    last_login_user_agent = models.CharField(max_length=255, blank=True, null=True, verbose_name="Último User Agent")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'cpf']

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        permissions = [
            ("can_manage_users", "Pode gerenciar usuários staff"),
            ("can_manage_memberships", "Pode gerenciar planos e matrículas"),
            ("can_view_financial_reports", "Pode visualizar relatórios financeiros"),
            ("can_manage_schedule", "Pode gerenciar horários e turmas"),
            ("can_checkin", "Pode realizar check-in na catraca"),
            ("can_manage_nutrition", "Pode gerenciar avaliações e cardápios"),
            ("can_view_student_data", "Pode visualizar dados dos alunos"),
            ("can_manage_trainings", "Pode gerenciar diários de treino"),
            ("can_view_system_logs", "Pode visualizar logs de auditoria do sistema"),
        ]

    def save(self, *args, **kwargs):
        # Sincroniza flags do Django com o tipo de usuário Rocks Fit
        # Se for superusuário (via CLI ou Admin), garante que o tipo seja SUPERADMIN
        if self.is_superuser:
            self.user_type = self.TYPE_SUPERADMIN
            self.is_staff = True
        
        elif self.user_type == self.TYPE_SUPERADMIN:
            self.is_superuser = True
            self.is_staff = True
        elif self.user_type in [self.TYPE_ADMIN, self.TYPE_SECRETARY]:
            self.is_staff = True
            if self.user_type == self.TYPE_ADMIN:
                self.is_superuser = False
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_user_type_display()}: {self.email}"

class LoginAttempt(models.Model):
    user_identifier = models.CharField(max_length=255, verbose_name="Email/CPF")
    ip_address = models.GenericIPAddressField(verbose_name="Endereço IP")
    user_agent = models.CharField(max_length=255, verbose_name="User Agent")
    success = models.BooleanField(default=False, verbose_name="Sucesso?")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora")

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Log de Acesso"
        verbose_name_plural = "Logs de Acessos"



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


class Trainer(OrderedModel):
    name = models.CharField(max_length=100)
    title = models.CharField(
        max_length=100, blank=True, null=True
    )  # Para o título como "Professor"
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="trainer_images/", blank=True, null=True)
    user = models.OneToOneField('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='trainer_profile', verbose_name="Usuário de Login")


    def __str__(self):
        return self.name

    class Meta(OrderedModel.Meta):
        verbose_name = "Professor"
        verbose_name_plural = "06. Academia: Professores"

class Nutritionist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='nutritionist_profile', verbose_name="Usuário de Login")
    name = models.CharField(max_length=100)
    crn = models.CharField(max_length=20, unique=True, null=True, blank=True, verbose_name="CRN")
    specialty = models.CharField(max_length=100, blank=True, null=True, verbose_name="Especialidade")
    bio = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="nutritionist_images/", blank=True, null=True)

    def __str__(self):
        return f"Dra(o). {self.name}"

    class Meta:
        verbose_name = "Nutricionista"
        verbose_name_plural = "06b. Academia: Nutricionistas"


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
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Modalidade")
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Professor")

    def __str__(self):
        trainer_name = self.trainer.name if self.trainer else "Sem Professor"
        return f"{self.get_day_display()} - {self.get_shift_display()} ({trainer_name})"

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
        ('semestral', 'Semestral'),
        ('anual', 'Anual'),
        ('bienal', 'Bienal'),
        ('personalizado', 'Personalizado (Ver campo Dias)'),
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
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='aluno_perfil', verbose_name="Usuário de Login")
    matricula = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="Matrícula")
    nome_completo = models.CharField(max_length=200, verbose_name="Nome Completo")
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True, verbose_name="CPF")
    data_nascimento = models.DateField(blank=True, null=True, verbose_name="Data de Nascimento")
    SEXO_CHOICES = (
        ('M', 'Masculino'),
        ('F', 'Feminino'),
        ('O', 'Outro'),
    )
    email = models.EmailField(verbose_name="E-mail")
    whatsapp = models.CharField(max_length=20, verbose_name="WhatsApp")
    STATUS_CHOICES = (
        ('ATIVO', 'Ativo'),
        ('AGUARDANDO', 'Aguardando Pagamento'),
        ('SUSPENSO', 'Suspenso'),
        ('INADIMPLENTE', 'Inadimplente'),
        ('INATIVO', 'Inativo'),
    )
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, blank=True, null=True, verbose_name="Sexo")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='INATIVO', verbose_name="Status de Gestão")
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Último Valor Pago")
    is_convenio = models.BooleanField(default=False, verbose_name="É Convênio? (Wellhub/TotalPass)")
    foto = models.ImageField(upload_to="alunos/fotos/", blank=True, null=True, verbose_name="Foto (Reconhecimento Facial)")
    digital = models.TextField(blank=True, null=True, verbose_name="Digital (Template Biométrico)")
    data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name="Data de Cadastro")
    
    # Endereço Completo
    cep = models.CharField(max_length=9, blank=True, null=True, verbose_name="CEP")
    endereco = models.CharField(max_length=255, blank=True, null=True, verbose_name="Endereço")
    numero = models.CharField(max_length=20, blank=True, null=True, verbose_name="Número")
    bairro = models.CharField(max_length=100, blank=True, null=True, verbose_name="Bairro")
    cidade = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cidade")
    estado = models.CharField(max_length=2, blank=True, null=True, verbose_name="UF")
    complemento = models.CharField(max_length=255, blank=True, null=True, verbose_name="Complemento")

    
    def is_active_pay(self):
        """Verifica se o aluno tem pagamento em dia"""
        from datetime import date
        hoje = date.today()
        if hasattr(self, 'acesso') and self.acesso.data_vencimento:
            return self.acesso.data_vencimento >= hoje
        return False

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
        verbose_name = "Aluno"
        verbose_name_plural = "02. Gestão: Alunos"
        permissions = [
            ("can_manage_students", "Pode gerenciar alunos no CRM"),
            ("can_access_financial", "Pode acessar o setor financeiro"),
        ]

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
    data_pagamento = models.DateTimeField(auto_now_add=True, verbose_name="Data do Pagamento")
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Valor Total")
    metodo_pagamento = models.CharField(max_length=50, blank=True, null=True, verbose_name="Método de Pagamento")

    def __str__(self):
        return f"{self.aluno.nome_completo} - {self.plano.name if self.plano else 'Sem Plano'} ({self.status})"

    class Meta:
        verbose_name = "Histórico de Pagamento"
        verbose_name_plural = "02. Gestão: Históricos de Pagamentos"

class CaixaTurno(models.Model):
    STATUS_CHOICES = [('ABERTO', 'Aberto'), ('FECHADO', 'Fechado')]
    operador = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Operador")
    abertura = models.DateTimeField(auto_now_add=True)
    fechamento = models.DateTimeField(null=True, blank=True)
    saldo_inicial = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Saldo Inicial (Abertura)")
    saldo_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Saldo Final (Fechamento)")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ABERTO')
    is_automatico = models.BooleanField(default=False, verbose_name="Fechamento Automático?")

    def __str__(self):
        return f"Caixa {self.id} - {self.operador.username} ({self.status})"

    class Meta:
        verbose_name = "Turno de Caixa"
        verbose_name_plural = "10. Financeiro: Turnos de Caixa"

class TransacaoCaixa(models.Model):
    TIPO_CHOICES = [('ENTRADA', 'Entrada (+)'), ('SAIDA', 'Saída (-)')]
    ORIGEM_CHOICES = [('MANUAL', 'Manual'), ('SITE', 'Site/Web'), ('APP', 'Aplicativo')]
    METODO_CHOICES = [('DINHEIRO', 'Dinheiro'), ('PIX', 'PIX'), ('CREDITO', 'Cartão de Crédito'), ('DEBITO', 'Cartão de Débito')]
    STATUS_CHOICES = [('NORMAL', 'Ativa'), ('ESTORNADO', 'Estornada')]
    
    caixa = models.ForeignKey(CaixaTurno, on_delete=models.CASCADE, related_name='transacoes')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    origem = models.CharField(max_length=10, choices=ORIGEM_CHOICES, default='MANUAL')
    metodo = models.CharField(max_length=15, choices=METODO_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='NORMAL')
    descricao = models.CharField(max_length=200)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_hora = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        sign = "+" if self.tipo == 'ENTRADA' else "-"
        return f"{sign} R$ {self.valor} ({self.descricao})"

    class Meta:
        verbose_name = "Movimentação de Caixa"
        verbose_name_plural = "11. Financeiro: Movimentações"

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
    esta_dentro = models.BooleanField(default=False, verbose_name="Está Dentro da Academia?")
    ultimo_acesso = models.DateTimeField(null=True, blank=True, verbose_name="Data/Hora Último Acesso")

    @property
    def dias_vencimento(self):
        from datetime import date
        if self.data_vencimento:
            diff = self.data_vencimento - date.today()
            return diff.days
        return None

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
    footer_description = models.TextField(blank=True, null=True, verbose_name="Descrição do Rodapé", default="Desenvolvido por Cleyson Cassio - Eng. de Software")

    # PIX Configuration
    pix_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="Chave PIX")
    pix_qrcode = models.ImageField(upload_to='pix/', blank=True, null=True, verbose_name="QR Code do PIX (Imagem)")

    def __str__(self):
        return "Configurações do Site"

    class Meta:
        verbose_name = "Configuração do Site"
        verbose_name_plural = "00. Configurações do Site"

class TrainerSocial(models.Model):
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='social_links', verbose_name="Professor")
    name = models.CharField(max_length=50, verbose_name="Nome da Rede (ex: Instagram)")
    link = models.URLField(verbose_name="Link do Perfil")
    icon_image = models.ImageField(upload_to='social_icons/trainers/', blank=True, null=True, verbose_name="Upload de Ícone (PNG/SVG)")
    icon_url = models.URLField(blank=True, null=True, verbose_name="Ou URL do Ícone (Externo)")

    def __str__(self):
        return f"{self.name} - {self.trainer.name}"

    class Meta:
        verbose_name = "Rede Social do Professor"
        verbose_name_plural = "08. Academia: Redes Sociais dos Professores"

class DeveloperSocial(models.Model):
    site_config = models.ForeignKey(SiteConfiguration, on_delete=models.CASCADE, related_name='social_links', verbose_name="Desenvolvedor (Rodapé)")
    name = models.CharField(max_length=50, verbose_name="Nome da Rede (ex: LinkedIn)")
    link = models.URLField(verbose_name="Link do Perfil")
    icon_image = models.ImageField(upload_to='social_icons/dev/', blank=True, null=True, verbose_name="Upload de Ícone (PNG/SVG)")
    icon_url = models.URLField(blank=True, null=True, verbose_name="Ou URL do Ícone (Externo)")

    def __str__(self):
        return f"{self.name} - Desenvolvedor"

    class Meta:
        verbose_name = "Rede Social do Desenvolvedor"
        verbose_name_plural = "09. Academia: Redes Sociais do Desenvolvedor"

# --- 🚀 SINCRONIZAÇÃO LOCAL (rks-catraca) ---
from django.db.models.signals import post_save
from django.dispatch import receiver
import json
import os

_sync_in_progress = False

@receiver(post_save, sender=Aluno)
def exportar_alunos_json(sender, instance, **kwargs):
    """ Gera um cache local em JSON para o Gestor de Alunos """
    global _sync_in_progress
    
    if os.environ.get('SKIP_SIGNALS') or _sync_in_progress:
        return
        
    _sync_in_progress = True
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
                'liberar_agora': a.acesso.abrir_catraca_agora if hasattr(a, 'acesso') else False,
                'foto_url': a.foto.url if a.foto else None,
                'tem_foto': bool(a.foto),
                'tem_digital': bool(a.digital)
            })
        from django.conf import settings
        caminho = os.path.join(settings.BASE_DIR, 'rks-catraca', 'alunos_local.json')
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump({'alunos': lista}, f, ensure_ascii=False, indent=4)
        
        # Resetar a flag de liberação após exportar (usando update para não redisparar o signal)
        from blog.models import ControleAcesso
        ControleAcesso.objects.filter(abrir_catraca_agora=True).update(abrir_catraca_agora=False)
        
        print(f"[SYNC] Arquivo local atualizado: {len(lista)} alunos.")
    except Exception as e:
        print(f"[SYNC] Erro ao gerar cache local: {e}")
    finally:
        _sync_in_progress = False

class RolePermission(models.Model):
    """Configuração de permissões por cargo do sistema"""
    role = models.CharField(max_length=20, choices=User.USER_TYPE_CHOICES, unique=True, verbose_name="Cargo")
    permissions = models.ManyToManyField('auth.Permission', blank=True, verbose_name="Permissões Ativas")

    def __str__(self):
        return f"Permissões: {self.get_role_display()}"

    class Meta:
        verbose_name = "Configuração de Cargo"
        verbose_name_plural = "06c. Configurações: Permissões por Cargo"

# Sinal para sincronizar RolePermission com Groups do Django
from django.db.models.signals import m2m_changed
from django.contrib.auth.models import Group

@receiver(m2m_changed, sender=RolePermission.permissions.through)
def sync_role_permissions_to_groups(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        # Nome do grupo correspondente ao cargo
        group_name = instance.get_role_display()
        group, created = Group.objects.get_or_create(name=group_name)
        
        # Sincroniza as permissões do cargo com o grupo
        group.permissions.set(instance.permissions.all())
        
        # Garante que todos os usuários deste tipo estejam no grupo
        users_of_type = User.objects.filter(user_type=instance.role)
        for user in users_of_type:
            user.groups.add(group)

class GymSetting(models.Model):
    name = models.CharField(max_length=100, default="Rocks-Fit")
    logo = models.ImageField(upload_to='gym_logos/', blank=True, null=True)
    
    # Configurações de Multas e Juros
    multa_atraso = models.DecimalField(max_digits=5, decimal_places=2, default=2.00, verbose_name="Multa por Atraso (%)", help_text="Percentual fixo aplicado sobre o valor da mensalidade atrasada.")
    juros_mensal = models.DecimalField(max_digits=5, decimal_places=2, default=1.00, verbose_name="Juros Mensais (%)", help_text="Percentual de juros aplicado por mês de atraso.")
    
    whatsapp_notificacao = models.CharField(max_length=20, blank=True, null=True, verbose_name="WhatsApp para Suporte", help_text="Número que o aluno deve chamar ao ser barrado.")

    # Mensagens Customizadas da Catraca
    msg_entrada = models.CharField(max_length=255, default="Bom treino!", verbose_name="Mensagem de Entrada")
    msg_saida = models.CharField(max_length=255, default="Bom descanso!", verbose_name="Mensagem de Saída")
    msg_aniversario = models.CharField(max_length=255, default="Parabéns! A Rocks Fit deseja um feliz aniversário! 🎉", verbose_name="Mensagem de Aniversário")
    msg_bloqueio_crm = models.CharField(max_length=255, default="Cadastro Suspenso/Inativo. Procure a recepção.", verbose_name="Mensagem de Bloqueio (Administrativo)")
    msg_erro_wellhub = models.CharField(max_length=255, default="Erro no plano Wellhub/Gympass. Valide no app.", verbose_name="Mensagem Erro Corporativo")
    
    CATRACA_FLUXO_CHOICES = [
        ('ENTRADA', 'Apenas Entrada'),
        ('SAIDA', 'Apenas Saída'),
        ('BIDIRECIONAL', 'Alternar Entrada/Saída Auto'),
    ]
    catraca_fluxo = models.CharField(max_length=20, choices=CATRACA_FLUXO_CHOICES, default='BIDIRECIONAL', verbose_name="Controle de Fluxo")
    
    # Configurações de IA
    ai_system_prompt = models.TextField(blank=True, null=True, verbose_name="Prompt de Sistema da IA")
    ai_api_key = models.CharField(max_length=255, blank=True, null=True, verbose_name="API Key (OpenRouter/Qwen)")

    def __str__(self):
        return f"Configurações de {self.name}"

    class Meta:
        verbose_name = "Configuração da Academia"
        verbose_name_plural = "Configuração da Academia"


class AnaliseGeralIA(models.Model):
    risco_evasao_percentual = models.FloatField(verbose_name="Risco de Evasão (%)")
    saude_financeira = models.TextField(verbose_name="Saúde Financeira")
    insight_do_dia = models.TextField(verbose_name="Insight do Dia")
    data_analise = models.DateTimeField(auto_now_add=True, verbose_name="Data da Análise")

    class Meta:
        verbose_name = "Análise Geral de IA"
        verbose_name_plural = "Análises Gerais de IA"
        ordering = ['-data_analise']


class AcaoIA(models.Model):
    TIPO_CHOICES = [
        ('POST_REDE_SOCIAL', 'Post Rede Social'),
        ('MENSAGEM_WHATSAPP', 'Mensagem WhatsApp'),
        ('CAMPANHA_EMAIL', 'Campanha de E-mail'),
        ('OUTRO', 'Outro'),
    ]
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('APROVADO', 'Aprovado'),
        ('REJEITADO', 'Rejeitado'),
        ('EXECUTADO', 'Executado'),
    ]
    id_acao = models.CharField(max_length=100, verbose_name="ID da Ação")
    tipo = models.CharField(max_length=50, choices=TIPO_CHOICES, verbose_name="Tipo")
    departamento = models.CharField(max_length=100, verbose_name="Departamento")
    titulo_painel = models.CharField(max_length=255, verbose_name="Título no Painel")
    detalhes_para_aprovacao = models.TextField(verbose_name="Detalhes para Aprovação")
    payload = models.JSONField(verbose_name="Dados da Ação (Payload)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE', verbose_name="Status")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")

    def __str__(self):
        return f"{self.titulo_painel} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Ação de IA"
        verbose_name_plural = "Ações de IA"
        ordering = ['-data_criacao']


class AcessoLog(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='acessos', verbose_name="Aluno")
    data_hora = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora")
    tipo = models.CharField(max_length=10, choices=[('ENTRADA', 'Entrada'), ('SAIDA', 'Saída')], default='ENTRADA')

    def __str__(self):
        return f"{self.aluno.nome_completo} - {self.tipo} em {self.data_hora}"

    class Meta:
        verbose_name = "Log de Acesso"
        verbose_name_plural = "Logs de Acessos"
        ordering = ['-data_hora']


# --- 🚀 AUTOMATIC PROFILE CREATION (SIGNALS) ---
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        def create_profile():
            try:
                # SE JÁ EXISTE PERFIL PARA ESTE USUÁRIO, NÃO FAZ NADA
                if hasattr(instance, 'aluno_perfil') or hasattr(instance, 'trainer_profile') or hasattr(instance, 'nutritionist_profile'):
                    return

                if instance.user_type == User.TYPE_STUDENT:
                    # Tenta vincular se o CPF já existir mas sem usuário, ou cria novo
                    aluno, created = Aluno.objects.get_or_create(
                        cpf=instance.cpf,
                        defaults={
                            'user': instance,
                            'nome_completo': f"{instance.first_name} {instance.last_name}",
                            'email': instance.email
                        }
                    )
                    if not created and not aluno.user:
                        aluno.user = instance
                        aluno.save()
                
                elif instance.user_type == User.TYPE_TRAINER:
                    Trainer.objects.get_or_create(
                        user=instance,
                        defaults={'name': f"{instance.first_name} {instance.last_name}"}
                    )
                elif instance.user_type == User.TYPE_NUTRITIONIST:
                    Nutritionist.objects.get_or_create(
                        user=instance,
                        defaults={'name': f"{instance.first_name} {instance.last_name}"}
                    )
            except Exception as e:
                logger.error(f"Erro ao criar perfil automático para {instance.email}: {e}")

        # Executa apenas após o Commit da transação principal (User)
        transaction.on_commit(create_profile)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        if instance.user_type == User.TYPE_STUDENT and hasattr(instance, 'aluno_perfil'):
            instance.aluno_perfil.save()
        elif instance.user_type == User.TYPE_TRAINER and hasattr(instance, 'trainer_profile'):
            instance.trainer_profile.save()
        elif instance.user_type == User.TYPE_NUTRITIONIST and hasattr(instance, 'nutritionist_profile'):
            instance.nutritionist_profile.save()
    except Exception:
        pass

# --- 🚀 SINCRONIZAÇÃO LOCAL (rks-catraca) ---
# ... (restante do código de exportação JSON já existente)

