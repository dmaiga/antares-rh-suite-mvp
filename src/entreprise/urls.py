from django.urls import path
from . import views

urlpatterns = [
    # Informations publiques
    path('info/', views.entreprise_info, name='entreprise-info'),
    path('savoir-plus/', views.savoir_plus, name='savoir-plus'),
    path('inscription/', views.entreprise_registry, name='entreprise-registry'),
    path('add_entreprise/', views.add_entreprise, name='add-entreprise'),
    path('confirmation/', views.confirmation_inscription, name='confirmation-inscription'),
    path('services/', views.services, name='services'),
    path('corbeille/', views.corbeille_entreprises, name='corbeille-entreprises'),
    path('<int:entreprise_id>/restaurer/', views.restaurer_entreprise, name='restaurer-entreprise'),
    path('<int:user_id>/rejeter/', views.rejeter_entreprise, name='rejeter-entreprise'),
    # Dashboard RH entreprise
    path('dashboard/', views.dashboard_rh, name='entreprise-dashboard'),

    # Listes d'entreprises
    path('liste/', views.entreprise_liste, name='entreprise-liste'),
    path('actives/', views.entreprises_actives, name='entreprise-actives'),
    path('desactivees/<int:user_id>/', views.entreprises_desactivees, name='entreprise-desactivees'),

    path('en-attente/', views.entreprises_en_attente, name='entreprise-en-attente'),

    # Actions sur entreprise
    path('approuver/<int:user_id>/', views.approuver_entreprise, name='entreprise-approuver'),
    path('reinitialiser-mot-de-passe/<int:user_id>/', views.reset_password_entreprise, name='entreprise-reset-password'),
    path('rejeter/<int:user_id>/', views.rejeter_entreprise, name='entreprise-rejet'),
    path('detail/<int:user_id>/', views.detail_entreprise, name='entreprise-detail'),

    # Activité récente
    path('activite-recente/', views.activite_recente, name='activite-recente'),
]
