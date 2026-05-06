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

from django.db import ProgrammingError, connection
import logging

logger = logging.getLogger(__name__)

class DatabasePermissionMiddleware:
    """
    Middleware de Auto-Recuperação:
    Se detectar "permission denied", tenta rodar o fix_db_permissions em tempo de execução.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, ProgrammingError) and "permission denied" in str(exception).lower():
            logger.warning(f"[AUTO-FIX] Erro de permissão detectado em {request.path}. Tentando correção automática...")
            
            try:
                from django.db import connection
                current_user = "unknown"
                with connection.cursor() as cursor:
                    cursor.execute("SELECT current_user;")
                    current_user = cursor.fetchone()[0]
                
                # Comandos rápidos de reparo
                commands = [
                    f"GRANT USAGE ON SCHEMA public TO \"{current_user}\";",
                    f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO \"{current_user}\";",
                    f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO \"{current_user}\";",
                    f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO \"{current_user}\";"
                ]
                
                with connection.cursor() as cursor:
                    for cmd in commands:
                        cursor.execute(cmd)
                
                logger.info("[AUTO-FIX] Permissões restauradas com sucesso.")
                
                # Se for GET, podemos tentar redirecionar para a mesma página
                if request.method == 'GET' and 'fixed=1' not in request.GET:
                    from django.shortcuts import redirect
                    path = request.get_full_path()
                    sep = '&' if '?' in path else '?'
                    return redirect(f"{path}{sep}fixed=1")
                    
            except Exception as e:
                logger.error(f"[AUTO-FIX] Falha na correção automática: {e}")
                
        return None
