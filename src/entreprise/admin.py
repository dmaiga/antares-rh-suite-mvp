from django.contrib import admin
from .models import Entreprise,ServiceRH,DemandeService,ServiceEntreprise,FactureLibre,NotificationEntreprise

admin.site.register(Entreprise)
admin.site.register(ServiceRH)
admin.site.register(DemandeService)
admin.site.register(ServiceEntreprise)
admin.site.register(FactureLibre)
admin.site.register(NotificationEntreprise)

class FactureLibreAdmin(admin.ModelAdmin):
    list_display = ('titre', 'entreprise', 'montant_ht', 'tva', 'montant_ttc', 'statut')
    readonly_fields = ('montant_tva', 'montant_ttc')