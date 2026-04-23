from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import User, LoginAttempt

class EmailOrCPFBackend(ModelBackend):
    """
    Autenticação personalizada permitindo login via Email ou CPF.
    Registra tentativas de login (sucesso/falha) para auditoria.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
            
        try:
            # Busca por email (principal) ou CPF (alternativo)
            user = User.objects.get(Q(email__iexact=username) | Q(cpf=username))
        except User.DoesNotExist:
            # Falha silenciosa para evitar enumeração de usuários, mas registra log
            self._log_attempt(request, username, success=False)
            return None
        except User.MultipleObjectsReturned:
            # Caso raríssimo dado as constraints de unique
            user = User.objects.filter(Q(email__iexact=username) | Q(cpf=username)).first()

        if user.check_password(password) and self.user_can_authenticate(user):
            self._log_attempt(request, username, success=True)
            # Atualiza metadados do usuário
            if request:
                user.last_login_ip = self._get_client_ip(request)
                user.last_login_user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
                user.save(update_fields=['last_login_ip', 'last_login_user_agent'])
            return user
        else:
            self._log_attempt(request, username, success=False)
            return None

    def _log_attempt(self, request, identifier, success):
        if request:
            LoginAttempt.objects.create(
                user_identifier=identifier,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                success=success
            )

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
