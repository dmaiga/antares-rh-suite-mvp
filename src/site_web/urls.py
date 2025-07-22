from django.urls import path
from . import views

urlpatterns = [
    path('home', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('jobs/', views.jobs, name='jobs'),
    path('contact/', views.contact, name='contact'),
    path('teams', views.teams, name='teams'),
     path('appointment', views.appointment, name='appointment'),
    path('login/', views.login, name='site_login'),
    path('entreprise_info/', views.entreprise_info, name='entreprise-info'),
    path('entreprise_registry/', views.entreprise_registry, name='entreprise-registry'),
    path('candidat/inscription/', views.candidat_register, name='candidate-registry'),
    path('entreprise/en_savoir_plus', views.savoir_plus, name='savoir-plus'),
    path('recruteur_info/', views.recruteur_info, name='recruteur-info'),
    path('rejoindre_team/', views.rejoindre_team, name='rejoindre-team'),






]