from django.contrib import admin
from .models import JobOffer

class JobOfferAdmin(admin.ModelAdmin):
    list_display = ('reference', 'titre', 'type_offre', 'statut', 'auteur', 'date_publication')
    list_filter = ('type_offre', 'statut', 'auteur__role')
    search_fields = ('reference', 'titre', 'auteur__first_name', 'auteur__last_name')

admin.site.register(JobOffer, JobOfferAdmin)
