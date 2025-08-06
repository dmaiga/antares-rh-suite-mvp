from django.urls import path
from . import views

urlpatterns = [

   path('statistique/', views.statistique_globale, name='statistique-utilisateur'),
   path('historique/mois/', views.historique_par_mois, name='historique-par-mois'),
   path('historique/jour/<str:date_str>/', views.historique_jour, name='historique-jour'),
   path('export/journee/<date>/', views.export_statistiques, name='export-journee'),
   path('export-semaine/<str:format>/<str:start_date_str>/', views.export_semaine, name='export-semaine'),
   
    path('historique_user/<int:user_id>/', views.historique_user, name='historique-employe'),
    path('historique_user/<int:user_id>/<str:semaine>/<str:jour>/', views.historique_detail_user, name='historique-detail-user'),
    path('commentaire/<int:tache_id>/', views.commentaire_tache, name='commentaire-tache'),
]
