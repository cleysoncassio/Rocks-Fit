from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied

def user_type_required(*user_types):
    """
    Decorador que verifica se o usuário possui um dos tipos permitidos.
    Exemplo: @user_type_required('admin', 'superadmin')
    """
    def check_user(user):
        if user.is_authenticated and (user.user_type in user_types or user.is_superuser):
            return True
        raise PermissionDenied
    return user_passes_test(check_user)

# Atalhos úteis
def admin_required(function):
    return user_type_required('admin', 'superadmin')(function)

def trainer_required(function):
    return user_type_required('trainer', 'admin', 'superadmin')(function)

def student_required(function):
    return user_type_required('student', 'admin', 'superadmin')(function)
