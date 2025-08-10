from django import forms
from django.forms import DateInput
from .models import JobOffer
from django_summernote.widgets import SummernoteWidget

class JobOfferForm(forms.ModelForm):
    # Common settings for list fields
    LIST_FIELD_CONFIG = {
        'mission_principale': {'rows': 3, 'label': "Missions principales"},
        'taches': {'rows': 5, 'label': "Tâches"},
        'competences_qualifications': {'rows': 5, 'label': "Compétences requises"},
        'conditions': {'rows': 3, 'label': "Conditions"},
        'profil_recherche': {'rows': 5, 'label': "Profil recherché"}
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configure list fields
        for field_name, config in self.LIST_FIELD_CONFIG.items():
            self.fields[field_name] = forms.CharField(
                widget=forms.Textarea(attrs={
                    'rows': config['rows'],
                    'placeholder': f"Une entrée par ligne\nExemple:\n- Première {config['label'].lower()}\n- Deuxième {config['label'].lower()}"
                }),
                label=config['label'],
                required=False
            )
        
        # Special fields
        self.fields['comment_postuler'].widget = SummernoteWidget(attrs={
            'summernote': {
                'toolbar': [
                    ['style', ['bold', 'italic', 'underline']],
                    ['para', ['ul', 'ol']],
                    ['insert', ['link']]
                ],
                'height': '250px',
            }
        })
        
        # Common attributes
        for field in self.fields.values():
            field.required = False
            if not isinstance(field.widget, (forms.CheckboxInput, forms.FileInput, SummernoteWidget)):
                field.widget.attrs.setdefault('class', 'form-control')
        
        # Specific attributes
        self.fields['visible_sur_site'].widget.attrs['class'] = 'form-check-input'
        self.fields['date_publication'].widget = DateInput(attrs={'type': 'date', 'class': 'form-control'})
        self.fields['date_limite'].widget = DateInput(attrs={'type': 'date', 'class': 'form-control'})

    class Meta:
        model = JobOffer
        fields = '__all__'
        exclude = ['auteur', 'date_creation', 'date_mise_a_jour', 'statut']
        help_texts = {
            'reference': "Format: ANT/STA/00002025",
            'fichier_pdf': "PDF optionnel (max. 5MB)",
        }

    def clean(self):
        cleaned_data = super().clean()
        # Additional custom validation can be added here 
        return cleaned_data