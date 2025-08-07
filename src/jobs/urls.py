from django.urls import path
from . import views

urlpatterns = [
    path('offres/', views.job_offer_list, name='job-offer-list'),
    path('offres/nouveau/', views.job_offer_create, name='job-offer-create'),
    path('offres/<int:pk>/', views.job_offer_detail, name='job-offer-detail'),
    path('offres/<int:pk>/modifier/', views.job_offer_update, name='job-offer-update'),
    path('offres/<int:pk>/supprimer/', views.job_offer_delete, name='job-offer-delete'),
    path('offres/<int:pk>/publier/', views.job_offer_publish, name='job-offer-publish'),
    path('offres/<int:pk>/depublier/', views.job_offer_unpublish, name='job-offer-unpublish'),
]
