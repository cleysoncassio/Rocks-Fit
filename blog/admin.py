from django import forms
from django.contrib import admin
from ordered_model.admin import OrderedModelAdmin

from .models import (ContactInfo, ContactMessage, Program,
                     Schedule, Trainer, Plan, Aluno, PagamentoHistorico, ControleAcesso, SiteConfiguration)


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    # This ensures only one instance is manageable, or at least makes it easier
    def has_add_permission(self, request):
        if self.model.objects.count() >= 1:
            return False
        return super().has_add_permission(request)

@admin.register(Plan)
class PlanAdmin(OrderedModelAdmin):
    list_display = ("name", "price", "period", "is_popular", "move_up_down_links")
    search_fields = ("name", "description")
    list_filter = ("is_popular",)


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
class TrainerAdmin(admin.ModelAdmin):
    list_display = ("name", "title", "instagram_url")
    search_fields = ("name",)


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
    search_fields = ("matricula", "nome_completo", "cpf", "whatsapp")
    list_filter = ("data_cadastro",)
    readonly_fields = ("matricula", "data_cadastro")

    def ver_foto(self, obj):
        from django.utils.html import format_html
        if obj.foto:
            return format_html('<img src="{}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover;" />', obj.foto.url)
        return "Sem Foto"
    ver_foto.short_description = "Foto"

@admin.register(PagamentoHistorico)
class PagamentoHistoricoAdmin(admin.ModelAdmin):
    list_display = ("aluno", "plano", "status", "data_pagamento", "metodo_pagamento")
    list_filter = ("status", "metodo_pagamento", "data_pagamento")
    search_fields = ("aluno__nome_completo", "aluno__matricula", "transacao_id")

@admin.register(ControleAcesso)
class ControleAcessoAdmin(admin.ModelAdmin):
    list_display = ("aluno", "data_vencimento", "status_catraca")
    list_filter = ("status_catraca", "data_vencimento")
    search_fields = ("aluno__nome_completo", "aluno__matricula")
