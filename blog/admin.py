from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from ordered_model.admin import OrderedModelAdmin

from .models import (ContactInfo, ContactMessage, Program,
                     Schedule, Trainer, Plan, Aluno, PagamentoHistorico, ControleAcesso, SiteConfiguration, TrainerSocial, DeveloperSocial, User, CaixaTurno, TransacaoCaixa, GymSetting)


class TrainerSocialInline(admin.TabularInline):
    model = TrainerSocial
    extra = 1
    fields = ('name', 'link', 'icon_image', 'icon_url', 'ver_previa')
    readonly_fields = ('ver_previa',)

    def ver_previa(self, obj):
        from django.utils.html import format_html
        if obj and obj.icon_image:
            return format_html('<img src="{}" style="width: 32px; height: 32px; background: #333; padding: 2px; border-radius: 4px;" />', obj.icon_image.url)
        elif obj and obj.icon_url:
            return format_html('<img src="{}" style="width: 32px; height: 32px; background: #333; padding: 2px; border-radius: 4px;" />', obj.icon_url)
        return "-"
    ver_previa.short_description = "Prévia"

class DeveloperSocialInline(admin.TabularInline):
    model = DeveloperSocial
    extra = 1
    fields = ('name', 'link', 'icon_image', 'icon_url', 'ver_previa')
    readonly_fields = ('ver_previa',)

    def ver_previa(self, obj):
        from django.utils.html import format_html
        if obj and obj.icon_image:
            return format_html('<img src="{}" style="width: 32px; height: 32px; background: #333; padding: 2px; border-radius: 4px;" />', obj.icon_image.url)
        elif obj and obj.icon_url:
            return format_html('<img src="{}" style="width: 32px; height: 32px; background: #333; padding: 2px; border-radius: 4px;" />', obj.icon_url)
        return "-"
    ver_previa.short_description = "Prévia"

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informações Pessoais', {'fields': ('first_name', 'last_name', 'email', 'avatar')}),
        ('Sistema: Cargo e Permissões', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'birth_date')}),
        ('Extra: Biografia e Localização', {'fields': ('bio', 'location', 'website')}),
        ('Datas Importantes', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_editable = ('role',)
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')

@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    inlines = [DeveloperSocialInline]
    fieldsets = (
        ('Header (Topo do Site)', {
            'fields': ('hero_title', 'hero_subtitle', 'hero_image', 'ver_previa_hero'),
        }),
        ('Branding & Logos', {
            'fields': (('intro_logo', 'footer_logo'), 'footer_description'),
        }),
        ('Financeiro: Chave PIX', {
            'fields': ('pix_key', 'pix_qrcode', 'ver_previa_pix'),
            'description': 'Configure as informações de recebimento para o checkout do aluno.'
        }),
        ('Imagens de Fundo (Parallax)', {
            'classes': ('collapse',),
            'fields': ('pricing_background', 'ps_parallax_background', 'contact_background', 'about_background', 'programs_background', 'trainers_background', 'schedule_background'),
        }),
    )
    readonly_fields = ('ver_previa_hero', 'ver_previa_pix')

    def ver_previa_hero(self, obj):
        from django.utils.html import format_html
        if obj and obj.hero_image:
            return format_html('<img src="{}" style="max-width: 200px; border-radius: 8px;" />', obj.hero_image.url)
        return "Sem imagem enviada."
    ver_previa_hero.short_description = "Prévia do Hero"

    def ver_previa_pix(self, obj):
        from django.utils.html import format_html
        if obj and obj.pix_qrcode:
            return format_html('<img src="{}" style="width: 150px; border-radius: 8px; border: 1px solid #ddd;" />', obj.pix_qrcode.url)
        return "Sem QR Code enviado."
    ver_previa_pix.short_description = "Prévia do PIX"

    def has_add_permission(self, request):
        if self.model.objects.count() >= 1:
            return False
        return super().has_add_permission(request)

    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }

@admin.register(Plan)
class PlanAdmin(OrderedModelAdmin):
    list_display = ("name", "price", "period", "is_popular", "move_up_down_links")
    list_editable = ("price", "period", "is_popular")
    search_fields = ("name", "description")
    list_filter = ("is_popular", "period", "plan_type")

    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'plan_type', 'duration_days', 'price', 'period', 'is_popular'),
        }),
        ('Conteúdo do Card', {
            'fields': ('description', 'features', 'card_button_text'),
        }),
        ('Configuração Financeira (Checkout)', {
            'description': 'Configure os botões e links que aparecerão no checkout deste plano.',
            'fields': (
                ('button1_text', 'infinitepay_link'), 
                ('button2_text', 'button2_url')
            ),
        }),
    )


@admin.register(Program)
class ProgramAdmin(OrderedModelAdmin):
    list_display = ("name", "ver_icone", "description", "move_up_down_links")
    search_fields = ["name"]
    list_filter = ("name",)

    def ver_icone(self, obj):
        from django.utils.html import format_html
        if obj.icon:
            return format_html('<img src="{}" style="width: 40px; height: 40px; object-fit: contain; background: #222; border-radius: 8px; padding: 4px;" />', obj.icon.url)
        return "Sem Ícone"
    ver_icone.short_description = "Ícone"


@admin.register(Trainer)
class TrainerAdmin(OrderedModelAdmin):
    list_display = ("name", "title", "move_up_down_links")
    list_editable = ("title",)
    search_fields = ("name", "title")
    inlines = [TrainerSocialInline]

    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }

@admin.register(TrainerSocial)
class TrainerSocialAdmin(admin.ModelAdmin):
    list_display = ("name", "trainer", "link", "ver_previa")
    list_editable = ("link",)
    list_filter = ("name", "trainer")
    readonly_fields = ("ver_previa",)

    def ver_previa(self, obj):
        from django.utils.html import format_html
        if obj.icon_image:
            return format_html('<img src="{}" style="width: 24px; height: 24px;" />', obj.icon_image.url)
        elif obj.icon_url:
            return format_html('<img src="{}" style="width: 24px; height: 24px;" />', obj.icon_url)
        return "-"
    ver_previa.short_description = "Ícone"

@admin.register(DeveloperSocial)
class DeveloperSocialAdmin(admin.ModelAdmin):
    list_display = ("name", "link", "ver_previa")
    list_editable = ("link",)
    readonly_fields = ("ver_previa",)

    def ver_previa(self, obj):
        from django.utils.html import format_html
        if obj.icon_image:
            return format_html('<img src="{}" style="width: 24px; height: 24px;" />', obj.icon_image.url)
        elif obj.icon_url:
            return format_html('<img src="{}" style="width: 24px; height: 24px;" />', obj.icon_url)
        return "-"
    ver_previa.short_description = "Ícone"


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("day", "shift", "start_time", "end_time", "trainer", "program")
    list_filter = ("day", "shift", "trainer", "program")
    search_fields = ("trainer__name", "program__name")
    ordering = ("day", "start_time")


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ("address", "phone", "email", "website")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at")
    list_filter = ("created_at",)
    search_fields = ["name", "email"]
    readonly_fields = ("created_at",)



@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ("matricula", "nome_completo", "cpf", "whatsapp", "data_cadastro", "ver_foto")
    search_fields = ("matricula", "nome_completo", "cpf", "whatsapp", "email")
    list_filter = ("data_cadastro",)
    readonly_fields = ("matricula", "data_cadastro")
    list_per_page = 20

    def ver_foto(self, obj):
        from django.utils.html import format_html
        if obj.foto:
            return format_html('<img src="{}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover;" />', obj.foto.url)
        return "Sem Foto"
    ver_foto.short_description = "Foto"

@admin.register(PagamentoHistorico)
class PagamentoHistoricoAdmin(admin.ModelAdmin):
    list_display = ("aluno", "plano", "status", "data_pagamento", "valor")
    list_editable = ("status",)
    list_filter = ("status", "data_pagamento", "plano")
    search_fields = ("aluno__nome_completo", "aluno__matricula", "transacao_id")

@admin.register(CaixaTurno)
class CaixaTurnoAdmin(admin.ModelAdmin):
    list_display = ("id", "operador", "status", "abertura", "fechamento", "saldo_inicial", "saldo_final")
    list_filter = ("status", "operador", "abertura")
    search_fields = ("operador__username",)

@admin.register(TransacaoCaixa)
class TransacaoCaixaAdmin(admin.ModelAdmin):
    list_display = ("data_hora", "tipo", "origem", "metodo", "valor", "descricao")
    list_filter = ("tipo", "origem", "metodo", "data_hora")
    search_fields = ("descricao",)

@admin.register(ControleAcesso)
class ControleAcessoAdmin(admin.ModelAdmin):
    list_display = ("aluno", "data_vencimento", "status_catraca")
    list_editable = ("data_vencimento", "status_catraca")
    list_filter = ("status_catraca", "data_vencimento")
    search_fields = ("aluno__nome_completo", "aluno__matricula")

@admin.register(GymSetting)
class GymSettingAdmin(admin.ModelAdmin):
    list_display = ('name', 'ver_logo')
    readonly_fields = ('ver_logo',)

    def ver_logo(self, obj):
        from django.utils.html import format_html
        if obj and obj.logo:
            return format_html('<img src="{}" style="height: 50px; background: #333; padding: 5px; border-radius: 8px;" />', obj.logo.url)
        return "Sem Logo"
    
    ver_logo.short_description = "Prévia da Logo"

    def has_add_permission(self, request):
        if self.model.objects.count() >= 1:
            return False
        return super().has_add_permission(request)
