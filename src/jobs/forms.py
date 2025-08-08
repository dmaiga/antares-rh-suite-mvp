from django import forms
from django.forms import DateInput
from .models import JobOffer
from django_summernote.widgets import SummernoteWidget, SummernoteInplaceWidget

class JobOfferForm(forms.ModelForm):
    # Surcharge des champs avec Summernote
    taches = forms.CharField(
        widget=SummernoteWidget(attrs={
            'summernote': {
                'toolbar': [
                    ['style', ['bold', 'italic', 'underline', 'clear']],
                    ['font', ['strikethrough']],
                    ['para', ['ul', 'ol', 'paragraph']],
                    ['insert', ['link', 'picture', 'video']],
                ],
                'height': '300px',
            }
        }),
        help_text="Description détaillée du poste"
    )
    competences_qualifications=  forms.CharField(
        widget=SummernoteWidget(attrs={
            'summernote': {
                'toolbar': [
                    ['style', ['bold', 'italic', 'underline', 'clear']],
                    ['font', ['strikethrough']],
                    ['para', ['ul', 'ol', 'paragraph']],
                    ['insert', ['link', 'picture', 'video']],
                ],
                'height': '300px',
            }
        }),
       
    )
    mission_principale=  forms.CharField(
        widget=SummernoteWidget(attrs={
            'summernote': {
                'toolbar': [
                    ['style', ['bold', 'italic', 'underline', 'clear']],
                    ['font', ['strikethrough']],
                    ['para', ['ul', 'ol', 'paragraph']],
                    ['insert', ['link', 'picture', 'video']],
                ],
                'height': '300px',
            }
        }),
        
    )


    profil_recherche = forms.CharField(
        widget=SummernoteWidget(attrs={
            'summernote': {
                'toolbar': [
                    ['style', ['bold', 'italic']],
                    ['para', ['ul', 'ol']],
                ],
                'height': '250px',
            }
        })
    )

    comment_postuler = forms.CharField(
        widget=SummernoteWidget(attrs={
            'summernote': {
                'toolbar': [
                    ['style', ['bold', 'italic', 'underline', 'clear']],
                    ['font', ['strikethrough']],
                    ['para', ['ul', 'ol', 'paragraph']],
                    ['insert', ['link', 'picture', 'video']],
                ],
                'height': '250px',
            }
        }),
        
    )

  
    class Meta:
        model = JobOffer
        fields = '__all__'
        exclude = ['auteur', 'date_creation', 'date_mise_a_jour']
        widgets = {
            'date_publication': DateInput(attrs={'type': 'date', 'class': 'datepicker'}),
            'date_limite': DateInput(attrs={'type': 'date', 'class': 'datepicker'}),
            'conditions': forms.Textarea(attrs={'rows': 2}),
            'type_offre': forms.Select(attrs={'class': 'select2'}),
            'statut': forms.Select(attrs={'class': 'select2'}),
            'secteur': forms.TextInput(attrs={'list': 'secteurs-list'}),
        }
        help_texts = {
            'reference': "Format: ANT/STA/00002025",
            'fichier_pdf': "Téléversez un PDF descriptif si disponible",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Style uniforme
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.FileInput, SummernoteWidget)):
                field.widget.attrs.update({'class': 'form-control'})
        
        self.fields['visible_sur_site'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['fichier_pdf'].widget.attrs.update({'class': 'form-control-file'})

  