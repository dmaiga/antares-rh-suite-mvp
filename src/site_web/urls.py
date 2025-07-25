from django.urls import path
from . import views

urlpatterns = [
    path('home', views.home, name='home'),
    path('about/', views.about, name='about'),

    path('jobs/', views.jobs, name='jobs'),
    path('contact/', views.contact, name='contact'),
    path('teams', views.teams, name='teams'),
     path('appointment', views.appointment, name='appointment'),
    path('login/', views.login, name='site_login'),
    path('candidat/inscription/', views.candidat_register, name='candidate-registry'),
   
    path('recruteur_info/', views.recruteur_info, name='recruteur-info'),
    path('rejoindre_team/', views.rejoindre_team, name='rejoindre-team'),






]