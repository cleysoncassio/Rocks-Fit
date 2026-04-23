from django.core.management.base import BaseCommand
from django.utils import timezone
from blog.models import LoginAttempt
from datetime import timedelta

class Command(BaseCommand):
    help = 'Remove logs de tentativa de login com mais de 30 dias para limpeza de banco'

    def handle(self, *args, **options):
        limit_date = timezone.now() - timedelta(days=30)
        deleted_count, _ = LoginAttempt.objects.filter(timestamp__lt=limit_date).delete()
        
        self.stdout.write(self.style.SUCCESS(f'Limpeza concluída: {deleted_count} logs removidos.'))
