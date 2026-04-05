from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "blog"
    verbose_name = "Rocks-Fit: Gestão e Design"

    def ready(self):
        try:
            from axes.apps import AxesConfig
            AxesConfig.verbose_name = "🛡️ Anti Hacking - Segurança"
        except ImportError:
            pass
