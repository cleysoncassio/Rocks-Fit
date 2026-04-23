from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.utils.translation import gettext_lazy as _
from .models import User

class EmailOrCPFAuthenticationForm(AuthenticationForm):
    """
    Formulário de login que aceita Email ou CPF no campo de username.
    """
    username = forms.CharField(
        label=_("E-mail ou CPF"),
        widget=forms.TextInput(attrs={"autofocus": True, "class": "form-control form-control-rocks", "placeholder": "E-mail ou CPF"})
    )
    password = forms.CharField(
        label=_("Senha"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "class": "form-control form-control-rocks", "placeholder": "Digite sua senha"})
    )

class RequestPasswordResetForm(PasswordResetForm):
    """
    Formulário de recuperação de senha com estilização Bootstrap.
    """
    email = forms.EmailField(
        label=_("E-mail"),
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email", "class": "form-control form-control-rocks", "placeholder": "Digite seu e-mail cadastrado"})
    )

class TOTPVerifyForm(forms.Form):
    """
    Formulário para verificação do código de 6 dígitos.
    """
    token = forms.CharField(
        label=_("Código 2FA"),
        max_length=6,
        widget=forms.TextInput(attrs={"class": "form-control form-control-rocks text-center", "placeholder": "000000", "style": "font-size: 2rem; letter-spacing: 0.5rem; color: #f27121;"})
    )
