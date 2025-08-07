from django.db import models
from authentication.models import User
from django.utils import timezone
from documents.models import chemin_document  
import os
from datetime import timedelta
from django.template.defaultfilters import floatformat
import logging
from django.http import FileResponse
logger = logging.getLogger(__name__)
from io import BytesIO
from reportlab.pdfgen import canvas
from django.core.files import File

from django.conf import settings


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
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='deleted_entreprises')

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

#-----------------------------------------------------------------------
#
#=======================================================================
#
#_______________________________________________________________________


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

#-----------------------------------------------------------------------
#
#=======================================================================
#
#_______________________________________________________________________


class DemandeService(models.Model):
    STATUT_CHOICES = [
        ('proposition', 'Proposition initiale RH'),
        ('accepte', 'Accepté par l\'entreprise'),
        ('contre_proposition', 'Contre-proposition reçue'),
        ('refuse', 'Refusé par l\'entreprise'),
        ('actif', 'Actif'),
        ('termine', 'Terminé'),
        ('suspendu', 'Suspendu'),
    ]

    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='demandes')
    service = models.ForeignKey(ServiceRH, on_delete=models.CASCADE)
    message = models.TextField(verbose_name="Détails de votre demande")
    pieces_jointes = models.FileField(upload_to='demandes/pieces_jointes/', blank=True, null=True)
    date_demande = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    statut = models.CharField(max_length=50, choices=STATUT_CHOICES, default='en_attente')

    class Meta:
        ordering = ['-date_demande']
        verbose_name = "Demande de service"
        verbose_name_plural = "Demandes de service"

    def peut_etre_modifiee(self):
        return self.statut in ['en_attente', 'en_cours']
    
    def accepter_proposition(self):
        """Appelé quand l'entreprise accepte la proposition"""
        self.statut = 'accepte'
        self.date_validation = timezone.now()
        self.save()
        
        # Activer le service après acceptation
        self.activer()
        
        # Notifier le backoffice
        NotificationEntreprise.objects.create(
            entreprise=self.entreprise,
            service=self,
            titre=f"Service accepté: {self.titre}",
            message=f"L'entreprise a accepté la proposition financière.",
            niveau='success',
            action_requise=False,
            source='client'
        )
    
    def soumettre_contre_proposition(self, contre_proposition_text):
        """Appelé quand l'entreprise fait une contre-proposition"""
        self.statut = 'contre_proposition'
        self.contre_proposition = contre_proposition_text
        self.save()
        
        # Notifier le backoffice
        NotificationEntreprise.objects.create(
            entreprise=self.entreprise,
            service=self,
            titre=f"Contre-proposition reçue: {self.titre}",
            message=f"L'entreprise a soumis une contre-proposition: {contre_proposition_text}",
            niveau='warning',
            action_requise=True,
            source='client'
        )
    def __str__(self):
        return f"{self.entreprise.nom} - {self.service.nom} ({self.get_statut_display()})"

#-----------------------------------------------------------------------
#
#=======================================================================
#
#_______________________________________________________________________


class ServiceEntreprise(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente de proposition'),                   
        ('proposition_envoyee', 'Proposition envoyée par Antares'),        
        ('en_revue', 'En revue par le client'),                    
        ('accepte', 'Accepté par le client'),                      
        ('contre_proposition', 'Contre-proposition envoyée'),        
        ('refuse', 'Refusé par Antares'),                                  
        ('valide', 'Contre-proposition acceptée par Antares'),            
        ('en_cours', 'En cours de traitement '),          
        ('actif', 'Service actif'),                                   
        ('suspendu', 'Service suspendu'),                              
        ('termine', 'Service terminé'),                                
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
    responsable_rh = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
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
            service=self,  # Ajout de la relation
            titre=f"Facture {self.titre}",
            description=f"Service {self.titre} ({self.periodicite_facturation})",
            montant=montant_total,
            statut='envoyee',
            envoyee_par=self.responsable_rh
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
    
    def soumettre_contre_proposition(self, contre_proposition_text):
        """Enregistre une contre-proposition de l'entreprise et met à jour le statut"""
        self.contre_proposition = contre_proposition_text
        self.statut = 'contre_proposition'
        self.save()
        
        # Optionally, you could add notification logic here
        # For example:
        NotificationEntreprise.objects.create(
            entreprise=self.entreprise,
            service=self,
            titre="Contre-proposition soumise",
            message=f"Une contre-proposition a été soumise pour le service {self.titre}",
            niveau='info',
            action_requise=True,
            source='entreprise'
        )

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

    
    def montant_ttc(self):
        return float(self.prix) * (1 + float(self.tva)/100)
    
    def prochaine_date_facturation(self):
        if self.periodicite_facturation == 'mensuelle':
            return timezone.now() + timedelta(days=30)
        elif self.periodicite_facturation == 'trimestrielle':
            return timezone.now() + timedelta(days=90)
        return None
    
    def duree_restante(self):
        if self.date_expiration:
            delta = self.date_expiration - timezone.now()
            return f"{delta.days} jours"
        return "Non défini"

    def generer_facture(self):
        montant_total = self.prix * (1 + self.tva / 100)
        facture = FactureLibre.objects.create(
            entreprise=self.entreprise,
            service=self,
            titre=f"Facture {self.titre}",
            description=f"Service {self.titre} ({self.periodicite_facturation})",
            montant=montant_total,
            statut='envoyee',
            envoyee_par=self.responsable_rh
        )

        try:
            # Ici  générer/sauvegarder le fichier PDF
            # facture.fichier_facture.save(f'facture_{facture.id}.pdf', pdf_file)
            pass
        except Exception as e:
            logger.error(f"Erreur génération facture {facture.id}: {str(e)}")
            facture.delete()
            raise
        
        return facture

    @property
    def montant_ttc_formate(self):
        """Retourne le montant TTC formaté"""
        ttc = float(self.prix) * (1 + float(self.tva)/100)
        return floatformat(ttc, 2)

#-----------------------------------------------------------------------
#
#=======================================================================
#
#_______________________________________________________________________


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

#-----------------------------------------------------------------------
#
#=======================================================================
#
#_______________________________________________________________________


import os
from io import BytesIO
from django.core.exceptions import ValidationError
from django.core.files import File
from django.db import models

class FactureLibre(models.Model):
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE, related_name='factures_libres')
    service = models.ForeignKey(
        'ServiceEntreprise',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='factures'
    )
    titre = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    fichier_facture = models.FileField(upload_to=chemin_document)
    envoyee_par = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="factures_envoyees")

    date_envoi = models.DateTimeField(auto_now_add=True)
    date_reception = models.DateTimeField(null=True, blank=True)

    statut = models.CharField(max_length=20, choices=[
        ('envoyee', 'Envoyée'),
        ('reçue', 'Reçue'),
        ('payee', 'Payée'),
    ], default='envoyee')

    preuve_paiement = models.FileField(upload_to='documents/preuves_paiement/', null=True, blank=True)
    commentaire_entreprise = models.TextField(blank=True)

    tva = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=18.0,
        verbose_name="Taux de TVA (%)"
    )
    montant_ht = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Montant HT"
    )

    @property
    def montant_tva(self):
        return self.montant_ht * self.tva / 100

    @property
    def montant_ttc(self):
        return self.montant_ht + self.montant_tva

    def fichier_existe(self):
        """Vérifie si le fichier est physiquement présent"""
        return bool(self.fichier_facture) and os.path.exists(self.fichier_facture.path)

    def clean(self):
        """Validation avant sauvegarde"""
        if self.service:
            if self.service.statut != 'accepte':
                raise ValidationError("Une facture ne peut être créée que pour un service accepté")
            if not self.service.date_validation:
                raise ValidationError("Le service doit avoir une date de validation")

    def save(self, *args, **kwargs):
        self.full_clean()  # Exécute les validations (clean)
        if not self.montant and self.montant_ht:
            self.montant = self.montant_ttc
        super().save(*args, **kwargs)

    def marquer_comme_payee(self, preuve):
        self.statut = 'payee'
        self.preuve_paiement = preuve
        self.save()

    def __str__(self):
        return f"{self.titre} - {self.entreprise.nom} ({self.montant} fcfa)"