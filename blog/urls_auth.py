from django.urls import path
from django.contrib.auth import views as auth_views
from .views_auth import (RocksFitLoginView, Setup2FAView, 
                        AdminDashboardView, StudentDashboardView, logout_view)

urlpatterns = [
    path('login/', RocksFitLoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Recuperação de Senha
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    
    # 2FA
    path('seguranca/2fa/setup/', Setup2FAView.as_view(), name='setup_2fa'),
    
    # Dashboards de Redirecionamento
    path('dashboard/admin/', AdminDashboardView.as_view(), name='dashboard_admin'),
    path('dashboard/aluno/', StudentDashboardView.as_view(), name='dashboard_student'),
]
