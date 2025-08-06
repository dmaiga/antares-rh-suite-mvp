from django.core.serializers.json import DjangoJSONEncoder
from datetime import date, timedelta,datetime
import json
from django.shortcuts import render, redirect,get_object_or_404
from django.utils import timezone
from todo.models import Tache, TacheSelectionnee, FichePoste, SuiviTache
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from collections import defaultdict
from calendar import monthrange,day_name
from django.db import transaction
from django.utils.timezone import localdate,now
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q,Sum
from django.db.models.functions import TruncMonth, TruncDate
import csv
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa  
from authentication.models import User
from django.contrib.auth import login, authenticate ,logout
from django.contrib import messages

def is_rh_or_admin(user):
    return user.is_authenticated and getattr(user, 'role', None) in ['admin', 'rh']

def get_performance_class(percentage):
    if percentage is None:
        return 'no-data'
    if percentage >= 90:
        return 'excellent'
    if percentage >= 70:
        return 'good'
    if percentage >= 50:
        return 'average'
    return 'poor'





JOURS_FR = {
    'Monday': 'Lundi',
    'Tuesday': 'Mardi',
    'Wednesday': 'Mercredi',
    'Thursday': 'Jeudi',
    'Friday': 'Vendredi',
    'Saturday': 'Samedi',
    'Sunday': 'Dimanche'
}

@login_required
def historique_par_mois(request):
    user_id = request.GET.get('user_id')
    is_rh_view = (
     user_id
     and str(request.user.id) != str(user_id)
     and is_rh_or_admin(request.user) )

    if user_id:
        user = get_object_or_404(User, id=user_id)
    else:
        user = request.user

    # Validation des paramètres
    mois = request.GET.get('mois')
    annee = request.GET.get('annee')
    
    if not mois or not annee:
        return redirect('statistique-utilisateur')
    
    try:
        mois = int(mois)
        annee = int(annee)
        date_debut = datetime(annee, mois, 1).date()
        _, dernier_jour = monthrange(annee, mois)
        date_fin = datetime(annee, mois, dernier_jour).date()
    except (ValueError, TypeError):
        return redirect('statistique-utilisateur')

    # Récupération des données par jour (uniquement du lundi au vendredi)
    jours_data = []
    current_date = date_debut
    
    while current_date <= date_fin:
        # Ne traiter que les jours de semaine (0=lundi, 4=vendredi)
        if current_date.weekday() < 5:  # 0-4 correspond à lundi-vendredi
            taches_jour = TacheSelectionnee.objects.filter(
                user=user,
                date_selection=current_date
            )
            
            total = taches_jour.count()
            terminees = taches_jour.filter(is_done=True).count()
            
            # Protection contre la division par zéro
            if total == 0:
                pourcentage = 0
                note = "Aucune tâche"
                badge_class = "bg-secondary"
            else:
                pourcentage = round((terminees / 6) * 100)
                
                # Évaluation qualitative basée sur 6 tâches max
                if terminees >= 6:
                    note = "🎉 Excellent"
                    badge_class = "bg-success"
                elif terminees == 5:
                    note = "✅ Très bien"
                    badge_class = "bg-primary"
                elif terminees >= 3:
                    note = "⚠️ Moyen"
                    badge_class = "bg-warning"
                else:
                    note = "🔴 Insuffisant"
                    badge_class = "bg-danger"
            
            jours_data.append({
                'date': current_date,
                'date_str': current_date.strftime('%d/%m'),
                'jour_semaine': JOURS_FR[current_date.strftime('%A')], 
                'total': total,
                'terminees': terminees,
                'pourcentage': pourcentage,
                'note': note,
                'badge_class': badge_class,
                'has_data': total > 0
            })
        
        current_date += timedelta(days=1)

    # Grouper par semaine (lundi-vendredi)
    semaines = []
    semaine_courante = []
    semaine_num = 1
    
    for jour in jours_data:
        # Nouvelle semaine chaque lundi
        if not semaine_courante or jour['date'].weekday() == 0:
            if semaine_courante:
                semaines.append({
                    'numero': semaine_num,
                    'debut': semaine_courante[0]['date'],
                    'fin': semaine_courante[-1]['date'],
                    'jours': semaine_courante
                })
                semaine_num += 1
            semaine_courante = []
        
        semaine_courante.append(jour)
    
    # Ajouter la dernière semaine
    if semaine_courante:
        semaines.append({
            'numero': semaine_num,
            'debut': semaine_courante[0]['date'],
            'fin': semaine_courante[-1]['date'],
            'jours': semaine_courante
        })

    # Noms des mois en français
    mois_noms = {
        1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
        5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
        9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
    }

    context = {
        'mois_nom': mois_noms.get(mois, ""),
        'annee_selected': annee,
        'semaines': semaines,
        'user_display_name': user.get_full_name() or user.username ,
        'is_rh_view': is_rh_view,
    }
    return render(request, 'statistiques/historique_mois.html', context)

@login_required
def historique_jour(request, date_str):
    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    user_id = request.GET.get('user_id')
    is_rh_view = (
     user_id
     and str(request.user.id) != str(user_id)
     and is_rh_or_admin(request.user) )
    
    if user_id:
        user = get_object_or_404(User, id=user_id)
    else:
        user = request.user
    # Récupérer les tâches
    taches = TacheSelectionnee.objects.filter(
        user=user,
        date_selection=date_obj
    ).select_related('tache')
    
    # Calcul des statistiques
    total = taches.count()
    terminees = taches.filter(is_done=True).count()
    pourcentage = round((terminees / total) * 100) if total else 0
    # Calcul du temps total et moyen
    suivis = SuiviTache.objects.filter(
        user=user,
        start_time__date=date_obj
    )
    
    duree_totale = sum((s.duree() for s in suivis), timedelta())
    moyenne = duree_totale / total if total > 0 else timedelta()
    
    context = {
        'date': date_obj,
        'user_display_name': user.get_full_name() or user.username,
        'taches': taches,
        'total': total,
        'terminees': terminees,
        'duree_totale': duree_totale,
        'duree_moyenne': moyenne,
        'jour': {
        'pourcentage': pourcentage
         },
        'is_rh_view': is_rh_view,
    }
    return render(request, 'statistiques/historique_jour.html', context)




@login_required
def export_statistiques(request, date):
    user = request.user
    date_obj = datetime.strptime(date, '%Y-%m-%d').date()

    taches = (
        TacheSelectionnee.objects
        .filter(user=user, date_selection=date_obj)
        .select_related("tache")
    )
    # Calcul des stats
    total = taches.count()
    terminees = taches.filter(is_done=True).count()
    pourcentage = round((terminees / total) * 100) if total else 0

    context = {
        'date': date_obj,
        'user': user,
        'taches': taches,
        'jour': {
            'pourcentage': pourcentage
        }
    }

    html = render_to_string("statistiques/pdf_export.html", context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="journee_{date}.pdf"'

    pisa_status = pisa.CreatePDF(BytesIO(html.encode('utf-8')), dest=response)
    if pisa_status.err:
        return HttpResponse("Erreur PDF", status=500)
    return response

@login_required
def statistique_globale(request):
    user = request.user
    today = now().date()

    # --- Statistiques du jour ---
    taches_auj = TacheSelectionnee.objects.filter(user=user, date_selection=today)
    total_selectionnees = taches_auj.count()
    terminees = taches_auj.filter(is_done=True).count()
    en_cours = taches_auj.filter(is_started=True, is_paused=False, is_done=False).count()
    en_pause = taches_auj.filter(is_paused=True, is_done=False).count()
    non_demarre = taches_auj.filter(is_started=False, is_paused=False, is_done=False).count()

    duree_totale = sum((s.duree() for s in SuiviTache.objects.filter(user=user, start_time__date=today)), timedelta())
    moyenne_par_tache = duree_totale / total_selectionnees if total_selectionnees > 0 else timedelta()

    historique_jour = []
    for sel in taches_auj:
        historique_jour.append({
            'titre': sel.tache.titre,
            'etat': sel.etat_courant,
            'duree': sel.duree_active(),
        })

    # --- Préparation des données pour les selecteurs ---
    mois_fr = [
        (1, "Janvier"), (2, "Février"), (3, "Mars"), (4, "Avril"),
        (5, "Mai"), (6, "Juin"), (7, "Juillet"), (8, "Août"),
        (9, "Septembre"), (10, "Octobre"), (11, "Novembre"), (12, "Décembre")
    ]
    
    # Années disponibles (de la première tâche à aujourd'hui)
    premiere_tache = TacheSelectionnee.objects.filter(user=user).order_by('date_selection').first()
    annee_min = premiere_tache.date_selection.year if premiere_tache else today.year
    annees = range(annee_min, today.year + 1)

    context = {
        'total': total_selectionnees,
        'terminees': terminees,
        'en_cours': en_cours,
        'en_pause': en_pause,
        'non_demarre': non_demarre,
        'duree_totale': duree_totale,
        'moyenne_tache': moyenne_par_tache,
        'historique': historique_jour,
        'mois_fr': mois_fr,
        'annees': reversed(annees),  # Affichage des années récentes en premier
    }
    return render(request, 'statistiques/statistique.html', context)



@login_required
def export_semaine(request, format, start_date_str):
    user = request.user
    start_date = parse_date(start_date_str)
    end_date = start_date + timedelta(days=6)

    taches = (
        TacheSelectionnee.objects
        .filter(user=user, date_selection__range=[start_date, end_date])
        .select_related('tache')
    )

    historique = defaultdict(list)
    jour_pourcentages = {}

    for t in taches:
        jour = t.date_selection
        if jour.weekday() < 5:  # Lundi à vendredi
            historique[jour].append(t)

    for jour, taches_du_jour in historique.items():
        total = len(taches_du_jour)
        terminees = sum(1 for t in taches_du_jour if t.is_done)
        pourcentage_jour = round((terminees / total) * 100) if total > 0 else 0
        jour_pourcentages[jour] = pourcentage_jour

    jours_effectifs = len(jour_pourcentages)
    pourcentage_global = round(sum(jour_pourcentages.values()) / jours_effectifs) if jours_effectifs else 0

    if pourcentage_global < 60:
        appreciation = "Insuffisant"
    elif pourcentage_global < 80:
        appreciation = "Bon"
    else:
        appreciation = "Excellent"

    if format == 'pdf':
        html = render_to_string("statistiques/semaine_pdf.html", {
            'historique': dict(historique),
            'start_date': start_date,
            'end_date': end_date,
            'user': user,
            'pourcentage': pourcentage_global,
            'appreciation': appreciation,
            'pourcentages_journaliers': jour_pourcentages,
        })

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="semaine_{start_date}.pdf"'

        pisa_status = pisa.CreatePDF(BytesIO(html.encode('utf-8')), dest=response)
        if pisa_status.err:
            return HttpResponse("Erreur de génération PDF", status=500)
        return response

    elif format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="semaine_{start_date}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Titre', 'État', 'Durée (min)', 'Commentaire RH', 'Commentaire Employé'])

        for date, taches_jour in dict(historique).items():
            for t in taches_jour:
                etat = "Terminée" if t.is_done else "En pause" if t.is_paused else "En cours" if t.is_started else "Non démarrée"
                writer.writerow([
                    date.strftime('%Y-%m-%d'),
                    t.tache.titre,
                    etat,
                    round(t.duree_active().total_seconds() / 60, 2),
                    t.commentaire_rh or t.tache.commentaire_rh or "",
                    t.commentaire_employe or ""
                ])
        return response

    return HttpResponse("Format non supporté", status=400)

# views.py
@login_required
@user_passes_test(is_rh_or_admin)
def historique_user(request, user_id):
    employe = get_object_or_404(User, id=user_id)
    today = now().date()
    semaines = []
    
    for i in range(4):  # 4 dernières semaines
        start_of_week = today - timedelta(days=today.weekday(), weeks=i)
        jours_semaine = [start_of_week + timedelta(days=j) for j in range(5)]  # Lundi à vendredi
        
        semaine_data = {
            'start': start_of_week,
            'end': start_of_week + timedelta(days=4),
            'jours': [],
            'moyenne': 0
        }
        
        total_percentage = 0
        
        for jour in jours_semaine:
            taches = TacheSelectionnee.objects.filter(
                user=employe,
                date_selection=jour,
                is_done=True
            ).select_related('tache__fiche_poste')
            
            done = taches.count()
            percentage = min(round((done / 6) * 100), 100)  # 6 tâches = 100%
            css_class = get_performance_class(percentage)
            total_percentage += percentage
            
            semaine_data['jours'].append({
                'date': jour,
                'done': done,
                'percentage': percentage,
                'css_class': css_class,
                'appreciation': get_appreciation(percentage)  # Nouvelle fonction
            })
        
        semaine_data['moyenne'] = round(total_percentage / len(jours_semaine)) if jours_semaine else 0
        semaines.append(semaine_data)
    
    context = {
        'employe': employe,
        'semaines': semaines,
    }
    return render(request, 'statistiques/historique_employe.html', context)

@login_required
@user_passes_test(is_rh_or_admin)
def historique_detail_user(request, user_id, semaine, jour):
    employe = get_object_or_404(User, id=user_id)
    date_jour = datetime.strptime(jour, '%Y-%m-%d').date()
    
    taches = TacheSelectionnee.objects.filter(
        user=employe,
        date_selection=date_jour,
        is_done=True
    ).select_related('tache__fiche_poste')
    
    taches_done = taches.count()
    pourcentage = min(round((taches_done / 6) * 100), 100)
    css_class = get_performance_class(pourcentage)
    appreciation = get_appreciation(pourcentage)
    
    context = {
        'employe': employe,
        'date_jour': date_jour,
        'taches': taches,
        'taches_done': taches_done,
        'pourcentage': pourcentage,
        'css_class': css_class,
        'appreciation': appreciation,
    }
    return render(request, 'statistiques/historique_detail_user.html', context)


def get_performance_class(percentage):
    if percentage >= 90: return 'Excellent'
    elif percentage >= 70: return 'Très bon'
    elif percentage >= 50: return 'Satisfaisant'
    else: return 'insuffissant'

def get_appreciation(percentage):
    if percentage >= 90: return 'Excellent'
    elif percentage >= 70: return 'Très bon'
    elif percentage >= 50: return 'Satisfaisant'
    elif percentage >= 30: return 'Insuffisant'
    else: return 'Médiocre'

@login_required
@user_passes_test(is_rh_or_admin)
def commentaire_tache(request, tache_id):
    tache = get_object_or_404(TacheSelectionnee, id=tache_id)
    if request.method == 'POST':
        commentaire = request.POST.get('commentaire', '').strip()
        if commentaire:
            tache.commentaire_rh = commentaire
            tache.save()
            messages.success(request, "💬 Commentaire ajouté à la tâche.")
    return redirect('historique-employe', user_id=tache.user.id)
