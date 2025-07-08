# authentication/forms.py
from django import forms
from .models import User

class LoginForm(forms.Form):
    username = forms.CharField(max_length=63, label='Nom d’utilisateur')
    password = forms.CharField(max_length=63, widget=forms.PasswordInput, label='Mot de passe')

class CreateUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
                    'username', 
                    'first_name',
                    'last_name', 
                    'email', 
                    'role', 
                    'start_date', 
                    'telephone_pro',
                 
                ]


class PersonalUserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name', 
            'email', 
            'photo',
            'telephone_perso',
            'ville',
            'quartier',
            'porte',
            'rue',
            'date_naissance',
            'contact_urgence',
            'poste_occupe',
        ]
 



class RHUserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email',
            'role', 'statut', 'start_date', 'end_date', 'telephone_pro'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
