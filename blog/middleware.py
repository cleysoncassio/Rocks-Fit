import time
from django.conf import settings
from django.contrib import auth
from django.shortcuts import redirect
from django.urls import reverse

class SessionTimeoutMiddleware:
    """
    Middleware para expirar sessões por inatividade.
    30 min para alunos, 60 min para staff.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        last_activity = request.session.get('last_activity')
        now = time.time()

        if last_activity:
            # Seleciona o timeout baseado no perfil
            timeout = 3600 if request.user.user_type != 'student' else 1800
            
            if now - last_activity > timeout:
                auth.logout(request)
                return redirect('login')

        request.session['last_activity'] = now
        return self.get_response(request)

class Enforce2FAMiddleware:
    """
    Obrigatoriedade de 2FA para SuperAdmin e Administrador.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Perfis que EXIGEM 2FA ativado
            enforced_roles = ['superadmin', 'admin']
            
            # Se for staff e estiver tentando acessar áreas seguras sem 2FA verificado
            if request.user.user_type in enforced_roles and not request.user.is_2fa_enabled:
                # Se não estiver no setup_2fa ou login, redireciona
                exempt_urls = [reverse('setup_2fa'), reverse('logout')]
                if request.path not in exempt_urls and not request.path.startswith('/admin/'):
                    return redirect('setup_2fa')
                    
        return self.get_response(request)
