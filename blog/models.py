from django.contrib.auth.models import AbstractUser
from django.db import models
from ordered_model.models import OrderedModel

class User(AbstractUser):
    """
    Modelo de Usuário ROCKS FIT.
    Atenção: Não redefinir 'groups' ou 'user_permissions' manualmente aqui.
    O Django cuida disso automaticamente via AbstractUser e AUTH_USER_MODEL.
    """
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=30, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to="user_avatars/", null=True, blank=True)
    website = models.URLField(max_length=100, blank=True)
    
    ROLE_CHOICES = (
        ('ADMIN', 'Administrador'),
        ('SECRETARIA', 'Secretaria'),
        ('PROFESSOR', 'Professor'),
        ('ALUNO', 'Aluno'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ALUNO', verbose_name="Cargo")

    class Meta:
        permissions = [
            ("can_access_financial", "Pode acessar o módulo financeiro e caixa"),
            ("can_manage_students", "Pode cadastrar e gerenciar alunos"),
            ("can_manage_workouts", "Pode gerenciar treinos e avaliações"),
            ("can_access_settings", "Pode acessar configurações do gestor"),
        ]

    def save(self, *args, **kwargs):
        # Configura staff status baseado no cargo
        if self.role == 'ADMIN':
            self.is_staff = True
            self.is_superuser = True
        elif self.role in ['SECRETARIA', 'PROFESSOR']:
            self.is_staff = True
            self.is_superuser = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


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
    title = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="trainer_images/", blank=True, null=True)
    user = models.OneToOneField('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='trainer_profile', verbose_name="Usuário de Login")

    def __str__(self):
        return self.name

    class Meta(OrderedModel.Meta):
        verbose_name = "Professor"
        verbose_name_plural = "06. Academia: Professores"


class Schedule(models.Model):
    DAY_CHOICES = [
        ("monday", "Segunda-feira"), ("tuesday", "Terça-feira"), ("wednesday", "Quarta-feira"),
        ("thursday", "Quinta-feira"), ("friday", "Sexta-feira"), ("saturday", "Sábado"), ("sunday", "Domingo"),
    ]
    SHIFT_CHOICES = [("manha", "Manhã"), ("meio_dia", "Meio-dia"), ("tarde", "Tarde"), ("noite", "Noite")]
    day = models.CharField(max_length=10, choices=DAY_CHOICES, verbose_name="Dia da Semana")
    shift = models.CharField(max_length=20, choices=SHIFT_CHOICES, default="manha", verbose_name="Turno")
    start_time = models.TimeField(verbose_name="Início")
    end_time = models.TimeField(verbose_name="Fim")
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Modalidade")
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Professor")

    def __str__(self):
        return f"{self.get_day_display()} - {self.get_shift_display()}"

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
        return f"Message from {self.name}"


class Plan(OrderedModel):
    PLAN_TYPE_CHOICES = [('diaria', 'Diária'), ('mensal', 'Mensal'), ('trimestral', 'Trimestral')]
    name = models.CharField(max_length=100, verbose_name="Nome do Plano")
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES, default='mensal', verbose_name="Tipo de Vencimento")
    duration_days = models.IntegerField(default=30, verbose_name="Dias de Acesso")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço")
    period = models.CharField(max_length=50, verbose_name="Período")
    description = models.TextField(verbose_name="Descrição Curta")
    is_popular = models.BooleanField(default=False, verbose_name="Mais Vendido?")
    features = models.TextField(verbose_name="Benefícios")
    card_button_text = models.CharField(max_length=50, blank=True, null=True, verbose_name="Texto do Botão")
    button1_text = models.CharField(max_length=100, blank=True, null=True)
    button1_url = models.URLField(blank=True, null=True)
    infinitepay_link = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta(OrderedModel.Meta):
        verbose_name = "Plano"
        verbose_name_plural = "03. Gestão: Planos"


class Aluno(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='aluno_perfil')
    matricula = models.CharField(max_length=20, unique=True, blank=True, null=True)
    nome_completo = models.CharField(max_length=200)
    cpf = models.CharField(max_length=14, unique=True)
    email = models.EmailField()
    whatsapp = models.CharField(max_length=20)
    status = models.CharField(max_length=15, default='ATIVO')
    foto = models.ImageField(upload_to="alunos/fotos/", blank=True, null=True)
    digital = models.TextField(blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.matricula} - {self.nome_completo}"

    class Meta:
        verbose_name = "Aluno"
        verbose_name_plural = "02. Gestão: Alunos"


class PagamentoHistorico(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='pagamentos')
    plano = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, default='pendente')
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    data_pagamento = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.aluno.nome_completo} - {self.status}"


class CaixaTurno(models.Model):
    operador = models.ForeignKey(User, on_delete=models.CASCADE)
    abertura = models.DateTimeField(auto_now_add=True)
    fechamento = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, default='ABERTO')

    class Meta:
        verbose_name = "Turno de Caixa"
        verbose_name_plural = "10. Financeiro: Turnos"


class TransacaoCaixa(models.Model):
    caixa = models.ForeignKey(CaixaTurno, on_delete=models.CASCADE, related_name='transacoes')
    tipo = models.CharField(max_length=10)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    descricao = models.CharField(max_length=200)

    class Meta:
        verbose_name = "Movimentação"
        verbose_name_plural = "11. Financeiro: Movimentações"


class ControleAcesso(models.Model):
    aluno = models.OneToOneField(Aluno, on_delete=models.CASCADE, related_name='acesso')
    data_vencimento = models.DateField(blank=True, null=True)
    status_catraca = models.CharField(max_length=25, default='bloqueado')
    abrir_catraca_agora = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Controle de Acesso"
        verbose_name_plural = "04. Gestão: Acesso"


class GymSetting(models.Model):
    name = models.CharField(max_length=100, default="Rocks-Fit")
    logo = models.ImageField(upload_to='gym_logos/', blank=True, null=True)

    class Meta:
        verbose_name = "Configuração da Academia"
        verbose_name_plural = "Configuração da Academia"
