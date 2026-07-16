from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Registro


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Usuário',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Usuário'}),
    )
    password = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Senha'}),
    )


class EntradaPresencialForm(forms.ModelForm):
    class Meta:
        model = Registro
        fields = ['data', 'entrada']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'entrada': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        }
        labels = {
            'data': 'Data',
            'entrada': 'Hora de entrada',
        }


class SaidaPresencialForm(forms.Form):
    saida = forms.TimeField(
        label='Hora de saída',
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
    )


class HomeOfficeForm(forms.ModelForm):
    class Meta:
        model = Registro
        fields = ['data', 'horas', 'descricao', 'anexo']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'horas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': '0.5'}),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': '• Descreva as atividades realizadas\n• Uma por linha',
            }),
            'anexo': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'data': 'Data',
            'horas': 'Quantidade de horas',
            'descricao': 'Descrição das atividades',
            'anexo': 'Anexo (opcional)',
        }


class RejeicaoForm(forms.Form):
    observacao = forms.CharField(
        label='Motivo da rejeição',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Ex: Descrição insuficiente.',
        }),
    )


class RelatorioForm(forms.Form):
    mes = forms.IntegerField(
        label='Mês',
        min_value=1,
        max_value=12,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    ano = forms.IntegerField(
        label='Ano',
        min_value=2020,
        max_value=2100,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
