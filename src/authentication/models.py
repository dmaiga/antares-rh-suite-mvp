from django.db import models
from django.contrib.auth.models import AbstractUser

class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
    
class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('rh', 'Ressources Humaines'),
        ('employe', 'Employé'),
        ('stagiaire', 'Stagiaire'),
        ('entreprise', 'Entreprise'),
        ('recruteur', 'Recruteur'),
        ('candidat', 'Candidat'),
    ]


    STATUT_CHOICES = [
        ('actif', 'Actif'),
        ('pause', 'En pause'),
        ('termine', 'Terminé'),
    ]
    
    CONTRACT_CHOICES = [
        ('cdi', 'CDI'),
        ('cdd', 'CDD'),
        ('stage', 'Stage'),
        ('interim', 'Intérim'),
    ]
    # Champs RH
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='actif')
    telephone_pro = models.CharField(max_length=20, blank=True)
    poste_occupe = models.CharField(max_length=100, blank=True)  

    # Adresse détaillée
    quartier = models.CharField(max_length=100, blank=True)
    rue = models.CharField(max_length=50, blank=True)
    porte = models.CharField(max_length=50, blank=True)
    ville = models.CharField(max_length=100, blank=True)

    # Champs personnels
    photo = models.ImageField(upload_to='avatars/', blank=True, null=True)
    telephone_perso = models.CharField(max_length=20, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    contact_urgence = models.CharField(max_length=100, blank=True)
    fiche_poste = models.ForeignKey('todo.FichePoste', null=True, blank=True, on_delete=models.SET_NULL, related_name='users')
    
    contract_type = models.CharField(max_length=10, choices=CONTRACT_CHOICES, blank=True)
    department = models.CharField(max_length=100, blank=True)  # Service/Département
    manager = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)  # Référent hiérarchique
    skills = models.ManyToManyField(Skill, blank=True)
    notes = models.TextField(blank=True)  # Notes RH
    last_evaluation = models.DateField(null=True, blank=True)  # Dernière évaluation
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Salaire
    working_hours = models.CharField(max_length=50, blank=True)  # Horaires de travail
    remote_days = models.PositiveIntegerField(default=0)  # Jours de télétravail/semaine
    
    # Fichiers
    cv = models.FileField(upload_to='cvs/', blank=True, null=True)
    contract_file = models.FileField(upload_to='contracts/', blank=True, null=True)
    
    # Champs recruteur
    fonction_recruteur = models.CharField(max_length=100, blank=True)
    cv_recruteur = models.FileField(upload_to='cvs/', blank=True, null=True)

    # Champs candidat
    niveau_etude = models.CharField(max_length=100, blank=True)
    experience = models.TextField(blank=True)
    domaines_recherche = models.CharField(max_length=255, blank=True)


    def __str__(self):
        return f"{self.get_full_name()} ({self.role})"

