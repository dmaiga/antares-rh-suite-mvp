from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from authentication.models import User
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
    PUBLIE = "publie", "Publié"
    EXPIRE = "expire", "Expiré"
    ARCHIVE = "archive", "Archivé"


class JobOffer(models.Model):
    # Référence et identification
    reference = models.CharField(
        max_length=100,
        unique=True,
        help_text="Référence unique commençant par ANT/STA (ex: ANT/STA/00002025)"
    )
    titre = models.CharField(
        max_length=255,
        verbose_name="Titre du poste"
    )
    type_offre = models.CharField(
        max_length=20,
        choices=JobType.choices,
        default=JobType.EMPLOI
    )
    
    # Informations sur la société
    societe = models.CharField(
        default='Antares',
        max_length=255,
        verbose_name="Société/Organisation",
        help_text="Nom de l'entreprise ou organisation proposant l'offre"
    )
    

    mission_principale = models.TextField(
        blank=True,
        null=True,
        help_text="Missions principales (une par ligne)"
    )
    taches = models.TextField(
        blank=True,
        null=True,
        help_text="Tâches spécifiques (une par ligne)"
    )
    
    # Profil recherché
    profil_recherche = models.TextField(
        verbose_name="Profil recherché",
        help_text="Description du profil idéal"
    )
    competences_qualifications = models.TextField(
        verbose_name="Compétences et qualifications",
        blank=True,
        null=True,
        help_text="Liste des compétences requises (une par ligne)"
    )
    niveau_etude = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Niveau d'étude requis"
    )
    experience_requise = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Expérience requise",
        help_text="Ex: '3 ans minimum en développement web'"
    )
    
    # Conditions
    conditions = models.TextField(
        blank=True,
        null=True,
        help_text="Conditions particulières (une par ligne)"
    )
    salaire = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Salaire/Indemnité"
    )
    
    # Informations pratiques
    lieu = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Lieu de travail"
    )
    comment_postuler = models.TextField(
        verbose_name="Comment postuler",
        help_text="Instructions pour postuler"
    )
    contact = models.EmailField(
        blank=True,
        verbose_name="Email de contact"
    )
    
    # Gestion des dates
    date_publication = models.DateField(
        default=timezone.now,
        verbose_name="Date de publication"
    )
    date_limite = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date limite de candidature"
    )
    
    # Métadonnées
    statut = models.CharField(
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.BROUILLON
    )
    visible_sur_site = models.BooleanField(
        default=True,
        verbose_name="Visible sur le site"
    )
    auteur = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Auteur"
    )
    secteur = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Secteur d'activité"
    )
    
    # Fichiers
    fichier_pdf = models.FileField(
        upload_to='offres_pdfs/',
        blank=True,
        verbose_name="PDF de l'offre",
        help_text="Format PDF uniquement"
    )
    
    # Dates techniques
    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_publication"]
        verbose_name = "Offre d'emploi"
        verbose_name_plural = "Offres d'emploi"
        permissions = [
            ("can_publish_offer", "Peut publier une offre"),
            ("can_manage_offer", "Peut gérer toutes les offres"),
        ]
    
    def __str__(self):
        return f"{self.reference} - {self.titre}"
    
    def clean(self):
        
        
        # Validation des dates
       
        
        if self.date_publication and self.date_limite and self.date_publication > self.date_limite:
            raise ValidationError("La date de publication ne peut pas être après la date limite")
    
    def get_clean_html(self, field_name):
        """
        Nettoie le HTML généré par Summernote avec bleach
        """
        html_content = getattr(self, field_name, '')
        if not html_content:
            return ''
        
        # Balises et attributs autorisés
        allowed_tags = ['a', 'p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 
                      'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'span', 'img']
        allowed_attributes = {
            'a': ['href', 'title', 'target', 'rel'],
            'img': ['src', 'alt', 'width', 'height', 'style']
        }
        
        cleaned_html = bleach.clean(
            html_content,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )
        
        return mark_safe(cleaned_html)
    
    def get_clean_description(self):
        return self.get_clean_html('description_poste')
    
    def get_clean_profil(self):
        return self.get_clean_html('profil_recherche')
    
    def get_clean_how_to_apply(self):
        return self.get_clean_html('comment_postuler')
    
    def format_liste(self, text):
        """Convertit un texte avec des lignes en liste HTML"""
        if not text:
            return ""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return mark_safe("<ul>" + "".join(f"<li>{line}</li>" for line in lines) + "</ul>")
    
    def get_missions_liste(self):
        return self.format_liste(self.mission_principale)
    
    def get_taches_liste(self):
        return self.format_liste(self.taches)
    
    def get_competences_liste(self):
        return self.format_liste(self.competences_qualifications)
    
    def get_conditions_liste(self):
        return self.format_liste(self.conditions)
    
    def est_expire(self):
        return self.date_limite and self.date_limite < timezone.now().date()
    
    def peut_postuler(self):
        return self.statut == JobStatus.PUBLIE and not self.est_expire()
    
    def get_status_badge_class(self):
        return {
            'brouillon': 'bg-warning',
            'publie': 'bg-success',
            'expire': 'bg-danger',
            'archive': 'bg-secondary'
        }.get(self.statut, 'bg-secondary')
    
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