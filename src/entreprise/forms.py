from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django import forms
from authentication.models import User
from entreprise.models import Entreprise, ServiceEntreprise, NotificationEntreprise,FactureLibre
from django.utils import timezone

class EntrepriseRegisterForm(forms.ModelForm):
    # Champs utilisateur (représentant) -
    email = forms.EmailField(required=True)
    first_name = forms.CharField(label="Prénom du représentant", max_length=150)
    last_name = forms.CharField(label="Nom du représentant", max_length=150)
    telephone_pro = forms.CharField(label="Téléphone professionnel", max_length=20)

    # Champs entreprise
    nom = forms.CharField(label="Nom de l'entreprise", max_length=255)
    secteur_activite = forms.CharField(label="Secteur d'activité", required=True)
    site_web = forms.CharField(
        label="Site web", 
        required=False,
        help_text="Exemple: www.monentreprise.com ou https://monentreprise.com"
    )
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
    
    accepte_cgv_cgu = forms.BooleanField(
        required=True,
        label="J'accepte les conditions générales",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        error_messages={
            'required': "Vous devez accepter les conditions pour continuer."
        }
    )
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'telephone_pro',
            'nom', 'secteur_activite', 'site_web', 'description',
            'adresse', 'ville', 'pays', 'taille_entreprise', 'logo',
            'accepte_cgv_cgu'
        ]

    def clean_site_web(self):
        site_web = self.cleaned_data.get('site_web', '').strip()
        
        if not site_web:
            return ''
            
        # Ajoutez http:// si ce n'est pas déjà présent
        if not site_web.startswith(('http://', 'https://')):
            site_web = 'http://' + site_web
            
        # Validation de l'URL
        validator = URLValidator()
        try:
            validator(site_web)
        except ValidationError:
            raise forms.ValidationError("Veuillez entrer une URL valide (ex: www.monentreprise.com)")
        
        return site_web  
    
    def save(self, commit=True):
        # Création de l'utilisateur sans username pour l'instant
        email_pro = self.cleaned_data['email']
        user = User(
            username=email_pro,  # ← utilisé comme identifiant unique
            email=email_pro,
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            telephone_pro=self.cleaned_data['telephone_pro'],
            role='entreprise',
            is_active=False
        )
        user.set_unusable_password()  # Pas de mot de passe utilisable initialement
        
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
                accepte_cgv_cgu=self.cleaned_data['accepte_cgv_cgu'],
                date_acceptation_cgv_cgu=timezone.now() if self.cleaned_data['accepte_cgv_cgu'] else None
            )
            
        return user
    



class CreateEntrepriseForm(forms.ModelForm):
    # Champs utilisateur
    email = forms.EmailField(required=True)
    first_name = forms.CharField(label="Prénom du représentant", max_length=150)
    last_name = forms.CharField(label="Nom du représentant", max_length=150)
    telephone_pro = forms.CharField(label="Téléphone professionnel", max_length=20)

    # Champs entreprise
    nom = forms.CharField(label="Nom de l'entreprise", max_length=255)
    secteur_activite = forms.CharField(label="Secteur d'activité", required=True)
    site_web = forms.CharField(
        label="Site web", 
        required=False,
        help_text="Exemple: www.monentreprise.com ou https://monentreprise.com"
    )
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
            'email', 'first_name', 'last_name', 'telephone_pro',
            'nom', 'secteur_activite', 'site_web', 'description',
            'adresse', 'ville', 'pays', 'taille_entreprise', 'logo'
        ]

    def clean_site_web(self):
        site_web = self.cleaned_data.get('site_web', '').strip()
        if not site_web:
            return ''
        if not site_web.startswith(('http://', 'https://')):
            site_web = 'http://' + site_web
        validator = URLValidator()
        try:
            validator(site_web)
        except ValidationError:
            raise forms.ValidationError("Veuillez entrer une URL valide (ex: www.monentreprise.com)")
        return site_web

    def save(self, commit=True):
        email_pro = self.cleaned_data['email']
        user = User(
            username=email_pro,
            email=email_pro,
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            telephone_pro=self.cleaned_data['telephone_pro'],
            role='entreprise',
            is_active=True
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
                accepte_cgv_cgu=True,  # puisque nous le faisons nous-mêmes
                date_acceptation_cgv_cgu=timezone.now(),
                statut='active',  # définir le statut comme actif
                approuvee=True 
            )

        return user




class ServiceEntrepriseForm(forms.ModelForm):
    class Meta:
        model = ServiceEntreprise
        fields = ['titre', 'description', 'prix', 'actif']
        labels = {
            'titre': "Titre du service",
            'description': "Description du service",
            'prix': "Prix (optionnel)",
            'actif': "Service actif ?",
        }


class NotificationEntrepriseForm(forms.ModelForm):
    class Meta:
        model = NotificationEntreprise
        fields = ['titre', 'message', 'niveau', 'action_requise', 'fichier']
        labels = {
            'titre': "Titre",
            'message': "Contenu de la notification",
            'niveau': "Niveau d'alerte",
            'action_requise': "Nécessite une action ?",
            'fichier': "Pièce jointe (facultative)"
        }


class FactureLibreForm(forms.ModelForm):
    class Meta:
        model = FactureLibre
        fields = ['titre', 'description', 'montant', 'fichier_facture']
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex : Facture Février 2025'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'montant': forms.NumberInput(attrs={'class': 'form-control'}),
            'fichier_facture': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
