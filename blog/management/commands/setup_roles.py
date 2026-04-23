from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from blog.models import User

class Command(BaseCommand):
    help = 'Configura os grupos e permissões iniciais do sistema'

    def handle(self, *args, **options):
        # 1. Definir os grupos (Perfís)
        roles = {
            'SuperAdmin': ['can_manage_users', 'can_view_system_logs', 'can_view_financial_reports', 'can_manage_memberships'],
            'Administrador': ['can_manage_memberships', 'can_view_financial_reports', 'can_manage_schedule', 'can_view_student_data'],
            'Secretário': ['can_manage_memberships', 'can_view_student_data'],
            'Professor': ['can_manage_trainings', 'can_view_student_data'],
            'Nutricionista': ['can_manage_nutrition', 'can_view_student_data'],
            'Aluno': ['can_checkin'],
        }

        user_content_type = ContentType.objects.get_for_model(User)

        for role_name, perms in roles.items():
            group, created = Group.objects.get_or_create(name=role_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Grupo "{role_name}" criado.'))

            # Atribuir as permissões ao grupo
            for codename in perms:
                try:
                    permission = Permission.objects.get(codename=codename, content_type=user_content_type)
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'Permissão "{codename}" não encontrada.'))

        self.stdout.write(self.style.SUCCESS('Carga de perfis e permissões concluída com sucesso.'))
