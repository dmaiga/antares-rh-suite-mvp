# entreprise/forms.py
from django import forms
from authentication.models import User
from entreprise.models import Entreprise

class EntrepriseRegisterForm(forms.ModelForm):
    # Champs utilisateur (représentant)
    email = forms.EmailField(required=True)
    username = forms.CharField(label="Nom d'utilisateur", max_length=150)
    first_name = forms.CharField(label="Prénom du représentant", max_length=150)
    last_name = forms.CharField(label="Nom du représentant", max_length=150)
    telephone_pro = forms.CharField(label="Téléphone professionnel", max_length=20)

    # Champs entreprise
    nom = forms.CharField(label="Nom de l'entreprise", max_length=255)
    secteur_activite = forms.CharField(label="Secteur d'activité", required=True)
    site_web = forms.URLField(label="Site web", required=False)
    description = forms.CharField(label="Description", widget=forms.Textarea, required=False)
    adresse = forms.CharField(label="Adresse", required=False)
    ville = forms.CharField(required=False)
    pays = forms.CharField(required=False)
    taille_entreprise = forms.ChoiceField(
        choices=[
            ('1-10', '1 à 10 employés'),
            ('11-50', '11 à 50 employés'),
            ('51-200', '51 à 200 employés'),
            ('200+', 'Plus de 200 employés'),
        ],
        required=False,
        label="Taille de l'entreprise"
    )
    logo = forms.ImageField(required=False, label="Logo de l'entreprise")

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 'telephone_pro',
            'nom', 'secteur_activite', 'site_web', 'description',
            'adresse', 'ville', 'pays', 'taille_entreprise', 'logo'
        ]

    def save(self, commit=True):
        user = User(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            telephone_pro=self.cleaned_data['telephone_pro'],
            role='entreprise',
            is_active=False
        )
        user.set_unusable_password()
        if commit:
            user.save()
            Entreprise.objects.create(
                user=user,
                nom=self.cleaned_data['nom'],
                secteur_activite=self.cleaned_data['secteur_activite'],
                site_web=self.cleaned_data.get('site_web'),
                description=self.cleaned_data.get('description'),
                adresse=self.cleaned_data.get('adresse'),
                ville=self.cleaned_data.get('ville'),
                pays=self.cleaned_data.get('pays'),
                taille_entreprise=self.cleaned_data.get('taille_entreprise'),
                logo=self.cleaned_data.get('logo'),
            )
        return user
