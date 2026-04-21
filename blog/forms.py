from django import forms

from .models import ContactMessage


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "message"]


from .models import Aluno

class AlunoForm(forms.ModelForm):
    class Meta:
        model = Aluno
        fields = [
            'nome_completo', 'cpf', 'data_nascimento', 'email', 
            'whatsapp', 'sexo', 'status', 'is_convenio', 'foto',
            'cep', 'endereco', 'numero', 'bairro', 'cidade', 'estado', 'complemento'
        ]

        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}),
        }

