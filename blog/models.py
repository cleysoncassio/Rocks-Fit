from django.contrib.auth.models import AbstractUser
from django.db import models
from ordered_model.models import OrderedModel
import datetime

class User(AbstractUser):
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
    icon = models.ImageField(upload_to="program_icons/", blank=True, null=True)
    join_url = models.URLField(blank=True, null=True)
    def __str__(self): return self.name
    class Meta(OrderedModel.Meta):
        verbose_name = "Modalidade"
        verbose_name_plural = "05. Academia: Modalidades"

class Trainer(OrderedModel):
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="trainer_images/", blank=True, null=True)
    user = models.OneToOneField('User', on_delete=models.SET_NULL, null=True, blank=True, related_name='trainer_profile')
    def __str__(self): return self.name
    class Meta(OrderedModel.Meta):
        verbose_name = "Professor"
        verbose_name_plural = "06. Academia: Professores"

class Schedule(models.Model):
    day = models.CharField(max_length=10, choices=[("monday", "Segun"), ("tuesday", "Terça")]) # Simplificado
    shift = models.CharField(max_length=20, default="manha")
    start_time = models.TimeField()
    end_time = models.TimeField()
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True)
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True)

class ContactInfo(models.Model):
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Plan(OrderedModel):
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, default='mensal')
    duration_days = models.IntegerField(default=30)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    period = models.CharField(max_length=50)
    description = models.TextField()
    is_popular = models.BooleanField(default=False)
    features = models.TextField()
    card_button_text = models.CharField(max_length=50, blank=True, null=True)
    button1_text = models.CharField(max_length=100, blank=True, null=True)
    button1_url = models.URLField(blank=True, null=True)
    button2_text = models.CharField(max_length=100, blank=True, null=True)
    button2_url = models.URLField(blank=True, null=True)
    infinitepay_link = models.URLField(blank=True, null=True)
    def __str__(self): return self.name
    class Meta(OrderedModel.Meta):
        verbose_name = "Plano"
        verbose_name_plural = "03. Gestão: Planos"

class Aluno(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='aluno_perfil')
    matricula = models.CharField(max_length=20, unique=True, blank=True, null=True)
    nome_completo = models.CharField(max_length=200)
    cpf = models.CharField(max_length=14, unique=True)
    data_nascimento = models.DateField(blank=True, null=True)
    sexo = models.CharField(max_length=1, blank=True, null=True)
    email = models.EmailField()
    whatsapp = models.CharField(max_length=20)
    status = models.CharField(max_length=15, default='ATIVO')
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_convenio = models.BooleanField(default=False)
    foto = models.ImageField(upload_to="alunos/fotos/", blank=True, null=True)
    digital = models.TextField(blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    cep = models.CharField(max_length=9, blank=True, null=True)
    endereco = models.CharField(max_length=255, blank=True, null=True)
    numero = models.CharField(max_length=20, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=2, blank=True, null=True)
    complemento = models.CharField(max_length=255, blank=True, null=True)
    def __str__(self): return self.nome_completo

class PagamentoHistorico(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='pagamentos')
    plano = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    transacao_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, default='pendente')
    data_pagamento = models.DateTimeField(auto_now_add=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    metodo_pagamento = models.CharField(max_length=50, blank=True, null=True)

class CaixaTurno(models.Model):
    operador = models.ForeignKey(User, on_delete=models.CASCADE)
    abertura = models.DateTimeField(auto_now_add=True)
    fechamento = models.DateTimeField(null=True, blank=True)
    saldo_inicial = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    saldo_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, default='ABERTO')

class TransacaoCaixa(models.Model):
    caixa = models.ForeignKey(CaixaTurno, on_delete=models.CASCADE, related_name='transacoes')
    tipo = models.CharField(max_length=10)
    origem = models.CharField(max_length=10, default='MANUAL')
    metodo = models.CharField(max_length=15)
    status = models.CharField(max_length=15, default='NORMAL')
    descricao = models.CharField(max_length=200)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_hora = models.DateTimeField(auto_now_add=True)

class ControleAcesso(models.Model):
    aluno = models.OneToOneField(Aluno, on_delete=models.CASCADE, related_name='acesso')
    data_vencimento = models.DateField(blank=True, null=True)
    status_catraca = models.CharField(max_length=25, default='bloqueado')
    abrir_catraca_agora = models.BooleanField(default=False)
    plano_pendente = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True)
    esta_dentro = models.BooleanField(default=False)
    ultimo_acesso = models.DateTimeField(null=True, blank=True)

class SiteConfiguration(models.Model):
    hero_title = models.CharField(max_length=200, blank=True, null=True)
    hero_image = models.ImageField(upload_to='site_images/', blank=True, null=True)
    def __str__(self): return "Config"

class GymSetting(models.Model):
    name = models.CharField(max_length=100, default="Rocks-Fit")
    logo = models.ImageField(upload_to='gym_logos/', blank=True, null=True)
    def __str__(self): return self.name
