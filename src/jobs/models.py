from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from authentication.models import User
from django.utils.safestring import mark_safe
import bleach
from django_summernote.models import AbstractAttachment
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from bs4 import BeautifulSoup
import bleach



class JobType(models.TextChoices):
    EMPLOI = "emploi", "Offre d'emploi"
    APPEL_OFFRE = "appel_offre", "Appel d'offres"
    AUTRE = "autre", "Autre"

class JobStatus(models.TextChoices):
    BROUILLON = "brouillon", "Brouillon"
    OUVERT = "ouvert", "Ouvert"
    EXPIRE = "expire", "Expiré"
    ARCHIVE = "archive", "Archivé"

class JobOffer(models.Model):
    # Core fields
    reference = models.CharField(max_length=100, unique=True)
    titre = models.CharField(max_length=255)
    type_offre = models.CharField(max_length=20, choices=JobType.choices, default=JobType.EMPLOI)
    societe = models.CharField(max_length=255, default='Antares')
    nombre_candidat = models.PositiveIntegerField(default=1, verbose_name="Nombre de candidats")

    # Content fields (automatically converted to lists)
    mission_principale = models.TextField(blank=True)
    taches = models.TextField(blank=True)
    profil_recherche = models.TextField(blank=True)
    competences_qualifications = models.TextField(blank=True)
    conditions = models.TextField(blank=True)
    comment_postuler = models.TextField()
    
    # Practical info
    lieu = models.CharField(max_length=255, blank=True)
    contact = models.EmailField(blank=True)
    salaire = models.CharField(max_length=100, blank=True)
    niveau_etude = models.CharField(max_length=100, blank=True, verbose_name="Niveau d'étude requis")
    experience_requise = models.CharField(max_length=100,blank=True,    verbose_name="Expérience requise",help_text="Ex: '3 ans minimum'")
    secteur = models.CharField(max_length=255, blank=True)
    fichier_pdf = models.FileField(upload_to='offres_pdfs/', blank=True)

    # Dates
    date_publication = models.DateField(default=timezone.now)
    date_limite = models.DateField(blank=True, null=True)
    
    # Metadata
    statut = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.BROUILLON)
    visible_sur_site = models.BooleanField(default=True)
    auteur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Technical
    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_publication"]
        verbose_name = "Offre d'emploi"
        verbose_name_plural = "Offres d'emploi"

    def __str__(self):
        return f"{self.reference} - {self.titre}"
    
    def save(self, *args, **kwargs):
        # Auto-convert text fields to HTML lists with better formatting
        list_fields = [
            'mission_principale', 
            'taches',
            'competences_qualifications',
            'conditions',
            'profil_recherche'
        ]
        
        for field in list_fields:
            text = getattr(self, field, '')
            if text and not text.strip().startswith('<ul>'):
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                html_content = "<ul style='margin-bottom: 1rem; padding-left: 1.5rem;'>"
                html_content += "".join(f"<li style='margin-bottom: 0.5rem; line-height: 1.5;'>{line}</li>" for line in lines)
                html_content += "</ul>"
                setattr(self, field, html_content)
        
        # Auto-set status
        today = timezone.now().date()
        if self.date_limite and self.date_limite < today:
            self.statut = JobStatus.EXPIRE
        elif self.visible_sur_site:
            self.statut = JobStatus.OUVERT
        
        super().save(*args, **kwargs)

    def clean(self):
        if self.date_limite and self.date_publication and self.date_limite <= self.date_publication:
            raise ValidationError("La date limite doit être postérieure à la date de publication")

    def get_clean_html(self, field_name):
        """Sanitize HTML content"""
        html_content = getattr(self, field_name, '')
        if not html_content:
            return ''
        
        allowed_tags = ['a', 'p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'div']
        allowed_attributes = {'a': ['href', 'title', 'target', 'rel']}
        
        return mark_safe(bleach.clean(
            html_content,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        ))
    


from django.db import models
from django_summernote.models import AbstractAttachment

class SummernoteAttachment(AbstractAttachment):
    offer = models.ForeignKey(
        JobOffer,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='attachments'
    )

    class Meta:
        verbose_name = "Pièce jointe"
        verbose_name_plural = "Pièces jointes"
    
    def __str__(self):
        return self.file.name