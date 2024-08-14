from django import forms
from django.contrib import admin
from .models import BlogPost
from .models import ContactInfo, ContactMessage, Trainer, Program, Schedule, Event


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ["name"]
    list_filter = ("name",)


@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ("name", "title", "instagram_url")
    search_fields = ("name",)


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("program", "Trainers", "day", "start_time", "end_time")
    list_filter = ("day", "program", "Trainers")
    search_fields = ["program__name", "Trainer__name"]


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ("address", "phone", "email", "website")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at")
    list_filter = ("created_at",)
    search_fields = ["name", "email"]
    readonly_fields = ("created_at",)


class BlogPostAdmin(admin.ModelAdmin):
    # Exibe os campos listados na visualização de lista no admin
    list_display = ("title", "author", "posted_on", "comments_count")

    # Adiciona um campo de busca para os campos indicados
    search_fields = ("title", "author", "content")

    # Adiciona filtros laterais para datas e autores
    list_filter = ("posted_on", "author")

    # Ordena os posts por data de postagem, do mais recente ao mais antigo
    ordering = ("-posted_on",)

    # Campos que aparecem na tela de detalhes
    fieldsets = (
        (None, {"fields": ("title", "author", "content", "image")}),
        (
            "Metadata",
            {
                "fields": ("posted_on", "comments_count"),
                "classes": ("collapse",),
            },
        ),
    )

    # Campos somente leitura
    readonly_fields = ("posted_on",)


admin.site.register(BlogPost, BlogPostAdmin)


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["title", "author", "description", "event_date", "comments_count"]

    def clean_event_date(self):
        event_date = self.cleaned_data.get("event_date")
        if not event_date:
            raise forms.ValidationError("The event date cannot be empty.")
        return event_date


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    form = EventForm
    list_display = ("title", "author", "event_date", "comments_count")
    search_fields = ("title", "author", "description")
    list_filter = ("event_date", "author")
    ordering = ("-event_date",)
    readonly_fields = ("comments_count",)
