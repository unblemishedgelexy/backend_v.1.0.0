from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    full_name = forms.CharField(required=False)
    mobile_number = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ('username', 'full_name', 'email', 'mobile_number', 'password1', 'password2')


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Email / Username / Mobile')
