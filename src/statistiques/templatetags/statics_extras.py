from django import template
from datetime import timedelta
import locale
register = template.Library()

@register.filter
def format_timedelta(value):
    """
    Formatte un timedelta ou une durée en secondes au format HH:MM:SS
    """
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
    elif isinstance(value, (int, float, str)):
        try:
            total_seconds = int(float(value))
        except (ValueError, TypeError):
            return str(value)
    else:
        return str(value)

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


@register.filter
def progress_bar(done, total):
    try:
        return "{:.0f}".format((done / total) * 100)
    except ZeroDivisionError:
        return "0"


@register.filter
def get_item(obj, key):
    try:
        return obj.get(key, [])
    except AttributeError:
        return []

@register.filter
def format_duree_hm(value):
    """
    Formatte une durée (timedelta, int ou string) en format court : HhMMmin
    """
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
    elif isinstance(value, (int, float, str)):
        try:
            total_seconds = int(float(value))
        except (ValueError, TypeError):
            return str(value)
    else:
        return str(value)

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours}h{minutes:02d}min"


@register.filter
def duration_to_minutes(value):
    if not value:
        return 0
    return round(value.total_seconds() / 60, 2)



@register.filter
def date_fr(value):
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
    return value.strftime('%A %d %B %Y') if value else ''

@register.filter
def mois_fr(value):
    mois = [
        'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
        'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
    ]
    return mois[value-1] if 1 <= value <= 12 else ''

def jour_fr(day_name):
    jours = {
        'Monday': 'Lundi',
        'Tuesday': 'Mardi',
        'Wednesday': 'Mercredi',
        'Thursday': 'Jeudi',
        'Friday': 'Vendredi',
        'Saturday': 'Samedi',
        'Sunday': 'Dimanche'
    }
    return jours.get(day_name, day_name)