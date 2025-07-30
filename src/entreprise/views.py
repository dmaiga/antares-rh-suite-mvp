
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from authentication.models import User
from .models import DemandeService
from .forms import EntrepriseRegisterForm,CreateEntrepriseForm
from django.contrib import messages
from django.utils import timezone
from entreprise.models import Entreprise
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.core.paginator import Paginator
from django.contrib.auth import login, authenticate ,logout
from django.http import HttpResponse, HttpResponseNotFound, Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.db.models import Count, Q,Prefetch, Case, When, IntegerField, Value, Sum, ExpressionWrapper, F, FloatField

#-------------------------------------------------------------------------------------
#                                       PUBLIC
#_____________________________________________________________________________________
def entreprise_info(request):
    return render(request, 'entreprise/public/entreprise_info.html')

def savoir_plus(request):
    return render(request, 'entreprise/public/savoir_plus.html')

def confirmation_inscription(request):
    return render(request, 'entreprise/public/confirmation_inscription.html')

def services(request):
    return render(request, 'entreprise/public/services.html')

def entreprise_registry(request):
    if request.method == 'POST':
        form = EntrepriseRegisterForm(request.POST, request.FILES)  # Important pour les fichiers
        if form.is_valid():
            form.save()
            return redirect('confirmation-inscription')
    else:
        form = EntrepriseRegisterForm()

    return render(request, 'entreprise/public/entreprise_registry.html', {
        'form': form,
        'form_title': 'Inscription Entreprise'
    })
#-------------------------------------------------------------------------------------
#                                       BACKEND
#_____________________________________________________________________________________
def is_rh_or_admin(user):
    return user.is_authenticated and user.role in ['admin', 'rh']

@login_required
@user_passes_test(is_rh_or_admin)
def dashboard_rh(request):
    # Statistiques principales basées sur le modèle
    stats = {
        'total_entreprises': Entreprise.objects.count(),
        'entreprises_actives': Entreprise.objects.filter(statut='active').count(),
        'entreprises_inactives': Entreprise.objects.filter(statut='inactive').count(),
        'entreprises_supprimees': Entreprise.objects.filter(statut='supprimer').count(),
        'entreprises_en_attente': User.objects.filter(
            role='entreprise', 
            is_active=False,
            entreprise__isnull=False
        ).count(),
        'derniere_validation': Entreprise.objects.filter(statut='active')
                              .order_by('-date_inscription')
                              .first().date_inscription if Entreprise.objects.filter(statut='active').exists() else "Jamais",
        'demandes_rh': DemandeService.objects.filter(statut='en_attente').count()
    }

    # Listes importantes
    entreprises_recentes = Entreprise.objects.filter(
        statut='active'
    ).select_related('user').order_by('-date_inscription')[:5]
    
    entreprises_en_attente = User.objects.filter(
        role='entreprise', 
        is_active=False,
        entreprise__isnull=False
    ).select_related('entreprise').order_by('-date_joined')[:5]
    
    demandes_rh = DemandeService.objects.filter(
        statut='en_attente'
    ).select_related('entreprise', 'service').order_by('-date_demande')[:5]

    context = {
        'stats': stats,
        'entreprises_recentes': entreprises_recentes,
        'entreprises_en_attente': entreprises_en_attente,
        'demandes_rh': demandes_rh,
        'section': 'dashboard',
    }
    return render(request, 'entreprise/backend/entreprise_dashboard.html', context)

@login_required
@user_passes_test(is_rh_or_admin)
def entreprises_en_attente(request):
    entreprises = User.objects.filter(  role='entreprise', is_active=False,  entreprise__isnull=False).select_related('entreprise')
    return render(request, 'entreprise/backend/entreprise_en_attente.html', {'entreprises': entreprises})

@login_required
@user_passes_test(is_rh_or_admin)
def approuver_entreprise(request, user_id):
    try:
        user = User.objects.get(id=user_id, role='entreprise')
        
        # Activer le compte utilisateur
        user.is_active = True
        user.save()
        
        # Marquer l'entreprise comme approuvée
        if hasattr(user, 'entreprise'):
            entreprise = user.entreprise
            entreprise.approuvee = True
            entreprise.statut = 'active'
            entreprise.save()
            
    # 3. Envoyer un e-mail avec identifiants (exemple simple, peut être amélioré)
    # send_mail(
    #     subject="Compte entreprise validé",
    #     message=f"Bonjour {user.username}, votre compte a été validé. Vous pouvez vous connecter avec vos identifiants.",
    #     from_email="noreply@antares.com",
    #     recipient_list=[user.email],
    # )
   
            messages.success(request, f"L'entreprise « {entreprise.nom} » a été approuvée avec succès.")
        else:
            messages.error(request, "Aucun profil entreprise associé à cet utilisateur.")
        
        return redirect('entreprise-liste')
    
    except User.DoesNotExist:
        messages.error(request, "Utilisateur entreprise introuvable.")
        return redirect('entreprise-liste')


@login_required
@user_passes_test(is_rh_or_admin)
def detail_entreprise(request, user_id):
    try:
        user = User.objects.select_related('entreprise').get(id=user_id, role='entreprise')
        entreprise = user.entreprise
    except (User.DoesNotExist, Entreprise.DoesNotExist):
        raise Http404("Entreprise introuvable")

    context = {
        'entreprise': entreprise,
        'services': entreprise.services.all(),
        'demandes': entreprise.demandes.select_related('service'),
        'notifications': entreprise.notifications.order_by('-date_envoi')[:5],
        'factures': entreprise.factures_libres.order_by('-date_envoi')
    }
    
    return render(request, 'entreprise/backend/entreprise_detail.html', context)


@login_required
@user_passes_test(is_rh_or_admin)
def add_entreprise(request):
    if request.method == 'POST':
        form = CreateEntrepriseForm(request.POST, request.FILES) 
        if form.is_valid():
            form.save()  # L'objet User ET Entreprise sont créés ici
            return redirect('entreprise-dashboard')
    else:
        form = CreateEntrepriseForm()
        print(form.errors)  

    return render(request, 'entreprise/backend/add_entreprise.html', {'form': form})

from django.db.models import Count, Q

@login_required
@user_passes_test(is_rh_or_admin)
def entreprise_liste(request):
    # Récupérer toutes les entreprises (sans filtre deleted par défaut)
    entreprises = Entreprise.objects.all().select_related('user').order_by('-date_inscription')

    # Filtres
    statut_filter = request.GET.get('statut')
    search_query = request.GET.get('search')

    # Filtre par statut
    if statut_filter in ['active', 'inactive', 'supprimer']:
        entreprises = entreprises.filter(statut=statut_filter)
    
    # Filtre par recherche
    if search_query:
        entreprises = entreprises.filter(
            Q(nom__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    # Récupérer les valeurs distinctes pour les filtres
    statuts = [choice[0] for choice in Entreprise._meta.get_field('statut').choices]

    # Pagination (10 par page)
    paginator = Paginator(entreprises, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'entreprise/backend/entreprise_liste.html', {
        'entreprises': page_obj,
        'statuts': statuts,
        'statut_filter': statut_filter,
        'search_query': search_query,
    })

@login_required
@user_passes_test(is_rh_or_admin)
def entreprises_actives(request):
    # Construction de la requête de base
    queryset = Entreprise.objects.filter(
        deleted=False,
        approuvee=True
    ).select_related('user').prefetch_related(
    Prefetch('demandes', queryset=DemandeService.objects.select_related('service').order_by('-date_demande'))
    )

    # Récupération des paramètres de filtrage
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    secteur_filter = request.GET.get('secteur', '')

    # Filtre par recherche
    if search_query:
        queryset = queryset.filter(
            Q(nom__icontains=search_query) |
            Q(secteur_activite__icontains=search_query) |
            Q(ville__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    # Filtre par statut
    if status_filter in ['active', 'inactive', 'pause']:
        queryset = queryset.filter(statut=status_filter)
    
    # Filtre par secteur
    if secteur_filter:
        queryset = queryset.filter(secteur_activite=secteur_filter)

    # Récupération des valeurs distinctes pour les filtres
    secteurs = Entreprise.objects.filter(deleted=False, approuvee=True) \
        .values_list('secteur_activite', flat=True) \
        .distinct().order_by('secteur_activite')

    # Pagination
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'secteur_filter': secteur_filter,
        'secteurs': secteurs,
    }
    return render(request, 'entreprise/backend/entreprise_actives.html', context)

@login_required
@user_passes_test(is_rh_or_admin)
def activite_recente(request):
    entreprises = Entreprise.objects.filter(approuvee=True).order_by('-date_inscription')[:10]
    return render(request, 'entreprise/backend/activite_recente.html', {'entreprises': entreprises})


@login_required
@user_passes_test(is_rh_or_admin)
def entreprises_desactivees(request, user_id):
    user = get_object_or_404(User, id=user_id, role='entreprise')
    entreprise = get_object_or_404(Entreprise, user=user)

    entreprise.approuvee = False
    entreprise.soft_delete(request.user, status='inactive')
    
    messages.success(request, "Le compte de l'entreprise a été désactivé.")
    return redirect('entreprise-detail', entreprise_id=entreprise.id)

from django.utils.crypto import get_random_string

@login_required
@user_passes_test(is_rh_or_admin)
def reset_password_entreprise(request, user_id):
    user = get_object_or_404(User, id=user_id, role='entreprise')
    new_password = get_random_string(10)
    user.set_password(new_password)
    user.save()
    
    # Optionnel : envoyer par email
    # send_mail(...)

    messages.success(request, f"Le mot de passe de {user.username} a été réinitialisé : {new_password}")
    return redirect('entreprise-detail', user_id=user.id)


@login_required
@user_passes_test(is_rh_or_admin)
def rejeter_entreprise(request, user_id):
    user = get_object_or_404(User, id=user_id, role='entreprise')
    
    try:
        entreprise = user.entreprise
        entreprise.soft_delete(request.user)
        messages.success(request, f"L'entreprise {entreprise.nom} a été mise dans la corbeille.")
    except Entreprise.DoesNotExist:
        messages.error(request, "Entreprise introuvable.")
    
    return redirect('entreprise-liste')

@login_required
@user_passes_test(is_rh_or_admin)
def corbeille_entreprises(request):
    entreprises = Entreprise.objects.filter(deleted=True).select_related('user', 'deleted_by')
    return render(request, 'entreprise/backend/corbeille.html', {'entreprises': entreprises})
  
@login_required
@user_passes_test(is_rh_or_admin)
def restaurer_entreprise(request, entreprise_id):
    entreprise = get_object_or_404(Entreprise, id=entreprise_id, deleted=True)
    
    entreprise.user.is_active = True
    entreprise.user.save()

    entreprise.deleted = False
    entreprise.deleted_at = None
    entreprise.deleted_by = None
    entreprise.statut = 'active'
    entreprise.approuvee = True
    entreprise.save()

    messages.success(request, f"L'entreprise {entreprise.nom} a été restaurée.")
    return redirect('corbeille-entreprises')