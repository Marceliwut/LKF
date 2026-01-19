from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User


class CustomSignupForm(UserCreationForm):
    email = forms.EmailField(label='Adres e-mail', required=True,
                             widget=forms.EmailInput(attrs={'placeholder': 'user@mail.com', 'class': 'form-control'}))

    first_name = forms.CharField(label='Imię', required=False,
                                 widget=forms.TextInput(attrs={'placeholder': 'Imię', 'class': 'form-control'}))
    last_name = forms.CharField(label='Nazwisko', required=False,
                                widget=forms.TextInput(attrs={'placeholder': 'Nazwisko', 'class': 'form-control'}))

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        labels = {
            'username': 'Nazwa użytkownika',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set widget attrs for username and password fields
        self.fields['username'].widget.attrs.update({'placeholder': 'np. Kamilek', 'class': 'form-control'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Wprowadź hasło', 'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Powtórz hasło', 'class': 'form-control'})


class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(label='Nazwa użytkownika lub e-mail', widget=forms.TextInput(attrs={'placeholder': 'Nazwa użytkownika lub e-mail', 'class': 'form-control'}))
    password = forms.CharField(label='Hasło', widget=forms.PasswordInput(attrs={'placeholder': 'Hasło', 'class': 'form-control'}))

    error_messages = {
        'invalid_login': "Błędna nazwa użytkownika/email lub hasło.",
        'inactive': "To konto jest nieaktywne.",
    }


class AdminResetPasswordForm(forms.Form):
    new_password = forms.CharField(label='Nowe hasło', widget=forms.PasswordInput(attrs={'placeholder': 'Nowe hasło', 'class': 'form-control'}))
    confirm_password = forms.CharField(label='Potwierdź hasło', widget=forms.PasswordInput(attrs={'placeholder': 'Potwierdź hasło', 'class': 'form-control'}))

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('new_password')
        confirm = cleaned_data.get('confirm_password')
        
        if password and confirm and password != confirm:
            raise forms.ValidationError("Hasła się nie zgadzają.")
        
        if password and len(password) < 8:
            raise forms.ValidationError("Hasło musi mieć co najmniej 8 znaków.")
        
        return cleaned_data


class ChangePasswordForm(forms.Form):
    current_password = forms.CharField(label='Bieżące hasło', widget=forms.PasswordInput(attrs={'placeholder': 'Wpisz bieżące hasło', 'class': 'form-control'}))
    new_password = forms.CharField(label='Nowe hasło', widget=forms.PasswordInput(attrs={'placeholder': 'Wpisz nowe hasło', 'class': 'form-control'}))
    confirm_password = forms.CharField(label='Potwierdź hasło', widget=forms.PasswordInput(attrs={'placeholder': 'Powtórz nowe hasło', 'class': 'form-control'}))

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('new_password')
        confirm = cleaned_data.get('confirm_password')
        
        if password and confirm and password != confirm:
            raise forms.ValidationError("Nowe hasła się nie zgadzają.")
        
        if password and len(password) < 8:
            raise forms.ValidationError("Hasło musi mieć co najmniej 8 znaków.")
        
        return cleaned_data


class MovieProposalForm(forms.Form):
    title = forms.CharField(
        label='Tytuł filmu',
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'Wpisz tytuł filmu', 'class': 'form-control', 'id': 'movieTitleInput'})
    )
    imdb_id = forms.CharField(
        label='IMDb ID',
        max_length=20,
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'imdbIdInput'})
    )
