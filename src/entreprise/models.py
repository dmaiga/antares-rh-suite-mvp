from django.db import models
from authentication.models import User
from django.utils import timezone
from documents.models import chemin_document  


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
    SERVICE_CHOICES = [
        ('recrutement', 'Recrutement - Trouvez les talents qui feront la différence dans votre organisation'),
        ('formation', 'Formation - Développez les compétences de vos équipes avec nos programmes sur mesure'),
        ('conseil_rh', 'Conseil RH - Optimisez votre gestion des ressources humaines avec notre expertise'),
        ('externalisation', 'Externalisation - Confiez-nous la gestion administrative de vos RH'),
        ('coaching', 'Coaching - Accompagnement personnalisé pour vos managers et talents'),
        ('audit_rh', 'Audit RH - Évaluez et améliorez vos processus RH'),
    ]

    code = models.CharField(max_length=50, choices=SERVICE_CHOICES, unique=True)
    nom = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        # Auto-remplir le nom à partir du choix
        if not self.nom:
            self.nom = dict(self.SERVICE_CHOICES).get(self.code, '').split(' - ')[0]
        if not self.description:
            self.description = dict(self.SERVICE_CHOICES).get(self.code, '').split(' - ')[1]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom

    @classmethod
    def initialize_services(cls):
        """Méthode pour initialiser les services en base de données"""
        for code, full_text in cls.SERVICE_CHOICES:
            cls.objects.get_or_create(code=code)

class DemandeService(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('acceptee', 'Acceptée'),
        ('refusee', 'Refusée'), 
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
    ]

    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='demandes')
    service = models.ForeignKey(ServiceRH, on_delete=models.CASCADE)
    message = models.TextField(verbose_name="Détails de votre demande")
    pieces_jointes = models.FileField(upload_to='demandes/pieces_jointes/', blank=True, null=True)
    date_demande = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES, default='en_attente')

    class Meta:
        ordering = ['-date_demande']
        verbose_name = "Demande de service"
        verbose_name_plural = "Demandes de service"

    def peut_etre_modifiee(self):
        return self.statut in ['en_attente', 'en_cours']

    def __str__(self):
        return f"{self.entreprise.nom} - {self.service.nom} ({self.get_statut_display()})"

class ServiceEntreprise(models.Model):
    STATUT_CHOICES = [
        ('en_cours', 'En cours de prestation'),
        ('proposition', 'Proposition RH'),
        ('rejete', 'Rejeté par l\'entreprise'),
        ('en_revue', 'En revue par l\'entreprise'),
        ('en_attente_activation', 'En attente activation'),
        ('accepte', 'Accepté par l\'entreprise'),
        ('actif', 'Actif'),
        ('termine', 'Terminé'),
        ('suspendu', 'Suspendu'), 
        ('contre_proposition', 'Contre-proposition reçue'),
        ('valide', 'Validé'),
        ('refuse', 'Refusé'),
    ]

    # Lien vers l'entreprise cliente
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='services')
    
    # Lien vers la demande initiale (optionnel)
    demandes = models.ManyToManyField(
        'DemandeService', 
        related_name='services_lies',
        blank=True
    )
    # Informations de base
    titre = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    conditions = models.TextField(blank=True, verbose_name="Conditions particulières")
    reponse_entreprise = models.TextField(blank=True)
    # Paramètres financiers
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    tva = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    periodicite_facturation = models.CharField(max_length=45, choices=[
        ('mensuelle', 'Mensuelle'),
        ('trimestrielle', 'Trimestrielle'),
        ('ponctuelle', 'Ponctuelle')
    ], default='mensuelle')
    
    # Statut et dates
    statut = models.CharField(max_length=50, choices=STATUT_CHOICES, default='proposition')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_activation = models.DateTimeField(null=True, blank=True)
    date_expiration = models.DateTimeField(null=True, blank=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    # Gestion RH
    responsable_rh = models.ForeignKey(User, on_delete=models.SET_NULL, 
                                     null=True, related_name='services_geres')
    notes_interne = models.TextField(blank=True)
    contre_proposition = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "Service personnalisé"
        verbose_name_plural = "Services personnalisés"
        ordering = ['-date_activation']

    def __str__(self):
        return f"{self.titre} - {self.entreprise.nom} ({self.get_statut_display()})"

    def activer(self):
        """Activer le service après acceptation par l'entreprise"""
        self.statut = 'actif'
        self.date_activation = timezone.now()
        premiere_demande = self.demandes.first()
        if premiere_demande:
            premiere_demande.statut = 'acceptee'
            premiere_demande.save()        
        self.save()

    def generer_facture(self):
        montant_total = self.prix * (1 + self.tva / 100)
        facture = FactureLibre.objects.create(
            entreprise=self.entreprise,
            titre=f"Facture {self.titre}",
            description=f"Service {self.titre} ({self.periodicite_facturation})",
            montant=montant_total,
            statut='envoyee'
        )
        NotificationEntreprise.objects.create(
            entreprise=self.entreprise,
            service=self,
            facture=facture,
            titre=f"Facture émise pour le service {self.titre}",
            message=f"Une facture de {montant_total} FCFA a été générée pour le service '{self.titre}'. Merci de procéder au paiement.",
            niveau='info',
            action_requise=True,
            source='backoffice'
        )
        return facture


    @classmethod
    def creer_depuis_demande(cls, demande):
        service = cls.objects.create(
            entreprise=demande.entreprise,
            titre=f"[PROPOSITION] {demande.service.nom}",
            description=demande.message,
            statut='proposition',
            prix=0
        )
        service.demandes.add(demande)  # Ajout de la relation
        return service
    


class NotificationEntreprise(models.Model):
    SOURCE_CHOICES = [
        ('client', 'Entreprise'),
        ('backoffice', 'Antares'),
    ]
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='notifications')
    service = models.ForeignKey(
        'ServiceEntreprise',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
        )
    facture = models.ForeignKey(
        'FactureLibre',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
        )

    titre = models.CharField(max_length=255)
    message = models.TextField()
    reponse_entreprise = models.TextField(blank=True, null=True)
    date_reponse = models.DateTimeField(blank=True, null=True)
    niveau = models.CharField(
        max_length=20,
        choices=[('info', 'Info'), ('alerte', 'Alerte'), ('urgent', 'Urgent')],
        default='info'
    )
    fichier = models.FileField(upload_to=chemin_document, null=True, blank=True)
    lu = models.BooleanField(default=False)
    date_envoi = models.DateTimeField(auto_now_add=True)
    action_requise = models.BooleanField(default=False)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='client')
    
    def __str__(self):
        return f"Notification pour {self.entreprise.nom} - {self.titre} - ({self.niveau})"



class FactureLibre(models.Model):
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='factures_libres')
    titre = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    fichier_facture = models.FileField(upload_to=chemin_document)
    envoyee_par = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="factures_envoyees")

    date_envoi = models.DateTimeField(auto_now_add=True)
    date_reception = models.DateTimeField(null=True, blank=True)
    
    statut = models.CharField(max_length=20, choices=[
        ('envoyee', 'Envoyée'),
        ('reçue', 'Reçue'),
        ('payee', 'Payée'),
    ], default='envoyee')

    preuve_paiement = models.FileField(upload_to='documents/preuves_paiement/' , null=True, blank=True)
    commentaire_entreprise = models.TextField(blank=True)
    
    def marquer_comme_payee(self, preuve):
        self.statut = 'payee'
        self.preuve_paiement = preuve
        self.save()

    def __str__(self):
        return f"{self.titre} - {self.entreprise.nom} ({self.montant} fcfa)"
