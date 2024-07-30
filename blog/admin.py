from django.contrib import admin

from .models import ContactInfo, ContactMessage, Instructor, Program, Schedule


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ["name"]
    list_filter = ("name",)


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ["name"]


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("program", "instructor", "day", "start_time", "end_time")
    list_filter = ("day", "program", "instructor")
    search_fields = ["program__name", "instructor__name"]


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ("address", "phone", "email", "website")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at")
    list_filter = ("created_at",)
    search_fields = ["name", "email"]
    readonly_fields = ("created_at",)
