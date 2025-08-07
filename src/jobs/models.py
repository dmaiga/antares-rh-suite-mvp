from django.db import models
from django.utils import timezone
from authentication.models import User

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
    reference = models.CharField(max_length=100, unique=True)
    titre = models.CharField(max_length=255)
    type_offre = models.CharField(max_length=20, choices=JobType.choices, default=JobType.EMPLOI)
    
    mission_principale = models.TextField()
    taches = models.TextField()
    profil_recherche = models.TextField()
    conditions = models.TextField(blank=True, null=True)
    autres_infos = models.TextField(blank=True, null=True)

    lieu = models.CharField(max_length=255, blank=True, null=True)
    date_publication = models.DateField(default=timezone.now)
    date_limite = models.DateField(blank=True, null=True)

    statut = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.BROUILLON)
    visible_sur_site = models.BooleanField(default=True)

    auteur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_mise_a_jour = models.DateTimeField(auto_now=True)
    secteur = models.CharField(max_length=255, blank=True)
    salaire = models.CharField(max_length=100, blank=True)
    niveau_etude = models.CharField(max_length=100, blank=True)
    experience_requise = models.CharField(max_length=100, blank=True)
    contact = models.EmailField(blank=True)
    fichier_pdf = models.FileField(upload_to='offres_pdfs/', blank=True)

    class Meta:
        ordering = ["-date_publication"]
    
    def __str__(self):
        return f"{self.reference} - {self.titre}"
    def form_valid(self, form):
        form.instance.auteur = self.request.user
        return super().form_valid(form)
