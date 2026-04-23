from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.urls import reverse_lazy
from django_otp.plugins.otp_totp.models import TOTPDevice
from .forms_auth import EmailOrCPFAuthenticationForm, TOTPVerifyForm
import qrcode
import io
import base64

class RocksFitLoginView(LoginView):
    template_name = 'registration/login.html'
    authentication_form = EmailOrCPFAuthenticationForm

    def get_success_url(self):
        """Redirecionamento inteligente baseado no perfil - SuperAdmin vai para o Enterprise"""
        user = self.request.user
        if user.user_type in ['superadmin', 'admin']:
            return reverse_lazy('crm_dashboard')
        elif user.user_type == 'secretary':
            return reverse_lazy('dashboard_secretary')
        elif user.user_type == 'trainer':
            return reverse_lazy('dashboard_trainer')
        elif user.user_type == 'nutritionist':
            return reverse_lazy('dashboard_nutritionist')
        else:
            return reverse_lazy('dashboard_student')

class Setup2FAView(LoginRequiredMixin, View):
    """
    Interface para o usuário ativar o 2FA via QR Code.
    """
    def get(self, request):
        if request.user.is_2fa_enabled:
            return render(request, 'registration/2fa_setup.html', {'already_enabled': True})
        
        # Cria ou obtém o dispositivo TOTP do usuário
        device, created = TOTPDevice.objects.get_or_create(user=request.user, name="default", confirmed=False)
        
        # Gera o QR Code
        otp_url = device.config_url
        img = qrcode.make(otp_url)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_base64 = base64.b64encode(buf.getvalue()).decode()

        return render(request, 'registration/2fa_setup.html', {
            'qr_code': qr_base64,
            'secret_key': device.key,
            'form': TOTPVerifyForm()
        })

    def post(self, request):
        form = TOTPVerifyForm(request.POST)
        if form.is_valid():
            token = form.cleaned_data['token']
            device = TOTPDevice.objects.get(user=request.user, confirmed=False)
            if device.verify_token(token):
                device.confirmed = True
                device.save()
                request.user.is_2fa_enabled = True
                request.user.save()
                return redirect('crm_dashboard')
            else:
                form.add_error('token', 'Código inválido. Tente novamente.')
        
        return render(request, 'registration/2fa_setup.html', {'form': form})

class AdminDashboardView(LoginRequiredMixin, View):
    def get(self, request):
        return redirect('crm_dashboard')

class StudentDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboards/student.html'

from django.contrib.auth import logout as auth_logout

def logout_view(request):
    """
    Desloga o usuário e redireciona imediatamente para o login.
    """
    auth_logout(request)
    return redirect('login')
