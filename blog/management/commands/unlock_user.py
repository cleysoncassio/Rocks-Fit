from django.core.management.base import BaseCommand
from axes.utils import reset
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Desbloqueia um usuário ou IP travado pelo django-axes'

    def add_arguments(self, parser):
        parser.add_argument('identifier', type=str, help='Email ou IP do usuário a ser desbloqueado')

    def handle(self, *args, **options):
        identifier = options['identifier']
        
        # Reseta por identificador (pode ser Username/Email ou IP)
        count = reset(username=identifier)
        if count == 0:
            count = reset(ip=identifier)
            
        if count > 0:
            self.stdout.write(self.style.SUCCESS(f'Sucesso: {identifier} foi desbloqueado.'))
        else:
            self.stdout.write(self.style.WARNING(f'Nenhum bloqueio encontrado para {identifier}.'))
