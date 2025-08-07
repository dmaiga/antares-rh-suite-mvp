from django import forms
from .models import JobOffer

class JobOfferForm(forms.ModelForm):
    class Meta:
        model = JobOffer
        fields = [
            'reference',
            'titre',
            'type_offre',
            'mission_principale',
            'taches',
            'profil_recherche',
            'conditions',
            'autres_infos',
            'lieu',
            'date_publication',
            'date_limite',
            'statut',
            'visible_sur_site',
            'secteur',
            'salaire',
            'niveau_etude',
            'experience_requise',
            'contact',
            'fichier_pdf',
        ]
        widgets = {
            'date_publication': forms.DateInput(attrs={'type': 'date'}),
            'date_limite': forms.DateInput(attrs={'type': 'date'}),
            'mission_principale': forms.Textarea(attrs={'rows': 4}),
            'taches': forms.Textarea(attrs={'rows': 4}),
            'profil_recherche': forms.Textarea(attrs={'rows': 4}),
            'conditions': forms.Textarea(attrs={'rows': 3}),
            'autres_infos': forms.Textarea(attrs={'rows': 3}),
        }
