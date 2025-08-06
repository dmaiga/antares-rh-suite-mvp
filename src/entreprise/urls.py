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
    #                                   CLIENT
    #=======================================================================================
    
    # Dashboard et vues principales
    path('', views.dashboard_client, name='dashboard-client'),
    path('services_client/', views.services_client, name='services-client'),
    
    # Gestion des demandes
    path('demandes/', views.demandes_client, name='demandes-client'),
    path('demandes/nouvelle/', views.demander_service, name='demander-service'),
    path('demandes/<int:demande_id>/annuler/', views.annuler_demande, name='annuler-demande'),
    #-----------------------------------------------------------------------------------------
    #05_08_2025 
    path('propositions/', views.liste_propositions_services, name='liste-propositions-services'),
    path('proposition/<int:service_id>/accepter/', views.accepter_proposition_service, name='accepter-proposition-service'),
    path('proposition/<int:service_id>/contre/', views.contre_proposition_service, name='contre-proposition-service'),
    path('demande/<int:demande_id>/', views.detail_demande_service, name='detail-demande-service'),
    path('services/', views.liste_services_entreprise, name='liste-services-entreprise'),



    #________________________________________________________________________________________
    # Factures
    path('factures/', views.factures_client, name='factures-client'),
    path('factures/<int:facture_id>/paiement/', views.upload_preuve_paiement, name='upload-preuve'),
    
    # Notifications
    path('notifications/', views.notifications_client, name='notifications-client'),
    path('notifications/envoyer/', views.envoyer_notification, name='envoyer-notification'),
    
    
    # Catalogue des services RH
    path('catalogue/', views.catalogue_services, name='catalogue-services'),

    
    #=======================================================================================
    #                                     BACKEND
    #=======================================================================================
    #06_08_2025
    path('propositions/creer/<int:service_id>/', views.creer_proposition_financiere, name='creer-proposition-financiere'),
    path('propositions/traiter/<int:service_id>/', views.traiter_reponse_proposition, name='traiter-reponse-proposition'),
    path('propositions/a-traiter/', views.liste_services_pour_traitement, name='liste-services-traitement'),
    
    #04_08_2025
    path('services/<int:service_id>/gerer-statut/', views.gerer_statut_service, name='gerer-statut-service'),
    path('entreprise/demandes/<int:demande_id>/refuser/', views.refuser_demande_motif, name='refuser-demande-motif'),

    path('entrelisterprise/<int:entreprise_id>/services/', views.liste_services_par_entreprise, name='services-par-entreprise'),
    path('entreprise/<int:entreprise_id>/factures/', views.liste_factures_par_entreprise, name='factures-par-entreprise'),
    path('entreprise/<int:entreprise_id>/notifications/', views.liste_notifications_par_entreprise, name='notifications-par-entreprise'),
    # Facture et notification - détails
    path('factures/listes', views.liste_toutes_factures, name='liste-toutes-factures'),
    path('factures/<int:facture_id>/', views.facture_detail, name='facture-detail'),
    path('notifications/entreprise', views.liste_notifications, name='liste-notifications'),

    path('notification/entreprise/<int:notification_id>/', views.notification_detail, name='notification-detail'),

    #_______________________________________________________________________________________
    path('entreprise/<int:entreprise_id>/demandes/', views.liste_demandes_client, name='liste-demandes-client'),
    path('demandes/<int:demande_id>/', views.consulter_demande, name='consulter-demande'),
    path('factures/creer/<int:entreprise_id>/', views.facture_libre_create, name='creer-facture-libre'),               
    path('services/<int:service_id>/', views.detail_service_client, name='service-client-detail'),
    
    path('demandes/<int:pk>/accepter/', views.demande_client_accepter, name='demande-client-accepter'),
    path('demandes/<int:pk>/refuser/', views.demande_client_refuser, name='demande-client-refuser'),
    
    # Dashboard RH entreprise
    path('entreprise/<int:entreprise_id>/notification/', views.envoyer_notification, name='envoyer-notification'),
    path('dashboard/', views.dashboard_rh, name='entreprise-dashboard'),
    path('add_entreprise/', views.add_entreprise, name='add-entreprise'),
    path('corbeille/', views.corbeille_entreprises, name='corbeille-entreprises'),
    
    # Services personnalisés
    path('services/creer/', views.creer_service, name='creer-service'),
    path('services/<int:service_id>/modifier/', views.modifier_service, name='modifier-service'),
    path('services/<int:service_id>/toggle/', views.toggle_service, name='toggle-service'),
    path('demandes_client/<int:demande_id>/',views.detail_demande_client,name='demande-client-detail'),
    path('demandes_client/<int:demande_id>/edit/', views.demande_client_edit,name='demande-client-edit'),
    path('list/demandes/', views.toutes_les_demandes_rh, name='toutes-demandes-rh'),

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
        