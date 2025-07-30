from django.db import models
from authentication.models import User
from django.utils import timezone

class Entreprise(models.Model):
    class StatutEntreprise(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        SUPPRIMEE = 'supprimer', 'Supprimée'

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
    statut = models.CharField(
        max_length=20,
        choices=StatutEntreprise.choices,
        default=StatutEntreprise.INACTIVE
        )

    rccm = models.CharField("RCCM", max_length=30, blank=True, null=True)

    date_inscription = models.DateTimeField(auto_now_add=True)
    accepte_cgv_cgu = models.BooleanField(
        default=False,
        verbose_name="Accepte les CG/PC"
    )
    date_acceptation_cgv_cgu = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date d'acceptation des CGV/CGU"
    )

    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='deleted_entreprises')

    def soft_delete(self, deleted_by_user, status='supprimer'):
        self.deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by_user
        self.statut = status
        self.user.is_active = False
        self.user.save()
        self.save()

    def save(self, *args, **kwargs):
        if self.accepte_cgv_cgu and not self.date_acceptation_cgv_cgu:
            self.date_acceptation_cgv_cgu = timezone.now()

        # Forcer le statut si deleted est True
        if self.deleted:
            self.statut = 'supprimer'
        else:
            if self.approuvee and self.statut != 'active':
                self.statut = 'active'
            elif not self.approuvee and self.statut != 'inactive':
                self.statut = 'inactive'

        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


class ServiceRH(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.nom


class DemandeService(models.Model):
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='demandes')
    service = models.ForeignKey(ServiceRH, on_delete=models.CASCADE)
    message = models.TextField()
    date_demande = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=30, choices=[
        ('en_attente', 'En attente'),
        ('acceptee', 'Acceptée'),
        ('refusee', 'Refusée'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
    ], default='en_attente')

    def __str__(self):
        return f"{self.entreprise.nom} - {self.service.nom}"

class ServiceEntreprise(models.Model):
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='services')
    titre = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    prix = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titre} ({self.entreprise.nom})"
    


class NotificationEntreprise(models.Model):
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='notifications')
    titre = models.CharField(max_length=255)
    message = models.TextField()
    niveau = models.CharField(
        max_length=20,
        choices=[
            ('info', 'Info'),
            ('alerte', 'Alerte'),
            ('urgent', 'Urgent')
        ],
        default='info'
    )
    lu = models.BooleanField(default=False)
    date_envoi = models.DateTimeField(auto_now_add=True)
    action_requise = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification pour {self.entreprise.nom} - {self.titre}"

class FactureLibre(models.Model):
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='factures_libres')
    titre = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    fichier_facture = models.FileField(upload_to='factures/')

    date_envoi = models.DateTimeField(auto_now_add=True)
    date_reception = models.DateTimeField(null=True, blank=True)
    
    statut = models.CharField(max_length=20, choices=[
        ('envoyee', 'Envoyée'),
        ('reçue', 'Reçue'),
        ('payee', 'Payée'),
    ], default='envoyee')

    preuve_paiement = models.FileField(upload_to='preuves_paiement/', null=True, blank=True)
    commentaire_entreprise = models.TextField(blank=True)

    envoyee_par = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.titre} - {self.entreprise.nom} ({self.montant} €)"
