# entreprise/templatetags/custom_tags.py
from django import template

register = template.Library()

@register.filter
def notif_icon(niveau):
    mapping = {
        'info': 'info-circle',
        'alerte': 'exclamation-triangle',
        'urgent': 'exclamation-circle',
        'suivi': 'clipboard-check',
    }
    return mapping.get(niveau, 'bell')  # valeur par défaut

@register.filter
def statut_color(statut):
    """
    Retourne une couleur Bootstrap adaptée à un statut.
    """
    mapping = {
        'en_attente': 'secondary',  # gris
        'en_cours': 'primary',      # bleu
        'terminee': 'success',      # vert
        'annulee': 'danger',        # rouge
        'bloquee': 'warning',       # jaune
    }
    return mapping.get(statut, 'light')  # couleur par défaut

@register.filter
def demande_status_color(statut):
    color_map = {
        'en_attente': 'warning',
        'acceptee': 'success',
        'refusee': 'danger',
        'en_cours': 'info',
        'terminee': 'secondary'
    }
    return color_map.get(statut, 'light')

@register.filter
def demande_status_color(status):
    color_map = {
        'en_attente': 'warning',
        'acceptee': 'success',
        'refusee': 'danger',
        'en_cours': 'info',
        'terminee': 'secondary'
    }
    return color_map.get(status, 'secondary')

@register.filter
def service_status_color(status):
    color_map = {
        'proposition': 'warning',
        'en_revue': 'info',
        'actif': 'success',
        'rejete': 'danger',
        'suspendu': 'secondary'
    }
    return color_map.get(status, 'secondary')

@register.filter
def historique_action_color(action):
    color_map = {
        'creation': 'primary',
        'modification': 'info',
        'acceptation': 'success',
        'refus': 'danger',
        'annulation': 'secondary'
    }
    return color_map.get(action, 'secondary')