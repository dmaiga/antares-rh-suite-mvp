from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
    
import re

def chemin_document(instance, filename):
    if instance.entreprise:
        nom_entreprise = re.sub(r'\W+', '_', instance.entreprise.nom.lower())
        type_doc = getattr(instance, 'type', 'autre')
        return f"documents/entreprise/{nom_entreprise}/{type_doc}/{filename}"
    return f"documents/general/{getattr(instance, 'type', 'autre')}/{filename}"


class Document(models.Model):
    TYPE_CHOICES = [
        ('fiche_candidat', 'Fiche de Candidature '),
        ('fiche_suivi', 'Fiche de suivi terrain'),
        ('admin', 'Document administratif'),
        ('grille', 'Grille Entretien'),
        ('contact','Liste contact'),
        ('candidature','Candidature Physique'),
        ('personnel','Suivi du personnel'),
        ('contrat', 'Contrat de travail'),
        ('dossier_agent','Dossier des agents'),
        ('autre', 'Autres'),
    ]

    VISIBILITE_CHOICES = [
        ('admin', 'Administrateur uniquement'),
        ('rh', 'RH uniquement'),
        ('employe', 'Employés'),
        ('stagiaire', 'Tout le monde'),
        ('temporaire', 'Accès temporaire'),
        ('prive', 'Privé (auteur uniquement)'),
    ]

    titre = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default='autre')
    fichier = models.FileField(upload_to=chemin_document)
    date_ajout = models.DateTimeField(auto_now_add=True)
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    visibilite = models.CharField(max_length=20, choices=VISIBILITE_CHOICES, default='rh')
    affectations = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='documents_attribues', blank=True)
    date_expiration_acces = models.DateField(null=True, blank=True)
    entreprise = models.ForeignKey(
        'entreprise.Entreprise',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='documents'
    )

    def est_expire(self):
        """Vérifie si l’accès temporaire est expiré"""
        if self.visibilite == 'temporaire' and self.date_expiration_acces:
            return timezone.now().date() > self.date_expiration_acces
        return False

    def __str__(self):
        return f"{self.titre} ({self.type})"
  
    def peut_etre_vu_par(self, user):
        if user.role in ['admin', 'rh']:
            return True
        if self.visibilite == 'prive':
            return self.auteur == user
        if self.visibilite == 'employe' and user.role == 'employe':
            return True
        if self.visibilite == 'stagiaire':
            return True 
        if self.visibilite == 'temporaire':
            return user in self.affectations.all() and not self.est_expire()
        if user in self.affectations.all():
            return True
        return False

