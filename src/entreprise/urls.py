from django.urls import path
from . import views

urlpatterns = [
    
    # Informations publiques
    path('info/', views.entreprise_info, name='entreprise-info'),
    path('savoir-plus/', views.savoir_plus, name='savoir-plus'),
    path('inscription/', views.entreprise_registry, name='entreprise-registry'),
    path('confirmation/', views.confirmation_inscription, name='confirmation-inscription'),
    path('services/', views.services, name='services'),
    
    #=======================================================================================
    #Entreprise CLIENT
    path('dashboard_client/', views.dashboard_client, name='dashboard-client'),
    path('services_client/', views.services_client, name='services-client'),
    path('demandes_client/', views.demandes_client, name='demandes-client'),


    #=======================================================================================
    #BACKEND#

    # Dashboard RH entreprise
    path('dashboard/', views.dashboard_rh, name='entreprise-dashboard'),
    path('add_entreprise/', views.add_entreprise, name='add-entreprise'),
    path('corbeille/', views.corbeille_entreprises, name='corbeille-entreprises'),
    
    
    # Listes d'entreprises
    path('liste/', views.entreprise_liste, name='entreprise-liste'),
    path('actives/', views.entreprises_actives, name='entreprise-actives'),
    path('en-attente/', views.entreprises_en_attente, name='entreprise-en-attente'),

    
    # Actions sur entreprise
    path('approuver/<int:entreprise_id>/', views.approuver_entreprise, name='entreprise-approuver'),
    path('reinitialiser-mot-de-passe/<int:entreprise_id>/', views.reset_password_entreprise, name='entreprise-reset-password'),
    path('rejeter/<int:entreprise_id>/', views.rejeter_entreprise, name='entreprise-rejet'),
    path('detail/<int:entreprise_id>/', views.detail_entreprise, name='entreprise-detail'),
    path('<int:entreprise_id>/restaurer/', views.restaurer_entreprise, name='restaurer-entreprise'),
    path('desactivees/<int:entreprise_id>/', views.entreprises_desactivees, name='entreprise-desactivees'),

    

    # Activité récente
    path('activite-recente/', views.activite_recente, name='activite-recente'),

]
        