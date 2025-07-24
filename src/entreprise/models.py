from django.db import models
from authentication.models import User

class Entreprise(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='entreprise')
    nom = models.CharField(max_length=255)
    secteur_activite = models.CharField(max_length=255)
    site_web = models.URLField(blank=True)
    description = models.TextField(blank=True)
    adresse = models.CharField(max_length=255, blank=True)
    ville = models.CharField(max_length=100, blank=True)
    pays = models.CharField(max_length=100, blank=True)
    taille_entreprise = models.CharField(max_length=50, blank=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    approuvee = models.BooleanField(default=False)
    date_inscription = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom
    
    @property
    def user_id(self):
        return self.user.id