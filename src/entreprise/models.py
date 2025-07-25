from django.db import models
from authentication.models import User
from django.utils import timezone

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
    rccm = models.CharField("RCCM", max_length=30, blank=True, null=True)
    statut = models.CharField(
        max_length=20,
        choices=[
            ('non_active', 'Non active'),
            ('active', 'Active'),
            ('pause', 'En pause'),
            ('terminee', 'Terminée'),
        ],
        default='non_active'
    )

    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='deleted_entreprises')

    def soft_delete(self, deleted_by_user):
        self.deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by_user
        self.save()
        # Désactiver aussi le compte utilisateur associé
        self.user.is_active = False
        self.user.save()

    def __str__(self):
        return self.nom
    
    @property
    def user_id(self):
        return self.user.id
    
    @property
    def profile_complete(self):
        required_fields = [self.ville, self.pays, self.secteur_activite, self.description]
        return all(field is not None and str(field).strip() != '' for field in required_fields)

    @property
    def profile_completion(self):
        fields = [self.ville, self.pays, self.secteur_activite, self.description]
        completed = sum(1 for field in fields if field is not None and str(field).strip() != '')
        return (completed * 100) // len(fields)