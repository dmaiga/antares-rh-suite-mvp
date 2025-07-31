
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from authentication.models import User
from .models import DemandeService,NotificationEntreprise
from .forms import EntrepriseRegisterForm,CreateEntrepriseForm,ServiceEntrepriseForm, NotificationEntrepriseForm,FactureLibreForm
                   
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
#___________________________________________________________________________________
#
@login_required
@user_passes_test(is_rh_or_admin)
def dashboard_rh(request):
    # Statistiques principales
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
    
    notifications = NotificationEntreprise.objects.select_related('entreprise')\
        .order_by('-date_envoi')[:10]
    
    context = {
        'stats': stats,
        'entreprises_recentes': entreprises_recentes,
        'entreprises_en_attente': entreprises_en_attente,
        'demandes_rh': demandes_rh,
        'notifications': notifications,
        'section': 'dashboard',
    }
    return render(request, 'entreprise/backend/entreprise_dashboard.html', context)

#___________________________________________________________________________________
#


@login_required
@user_passes_test(is_rh_or_admin)
def entreprise_liste(request):
    # Récupérer toutes les entreprises (sans filtre deleted par défaut)
    entreprises = Entreprise.objects.all().select_related('user').order_by('-date_inscription')

    # Filtres
    statut_filter = request.GET.get('statut')
    search_query = request.GET.get('search')
    if search_query in [None, '', 'None']:
        search_query = None

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
#___________________________________________________________________________________
#

@login_required
@user_passes_test(is_rh_or_admin)
def detail_entreprise(request, entreprise_id):
    entreprise = get_object_or_404(
        Entreprise.objects.select_related('user').prefetch_related(
            'services',
            'services__demandes',
            'notifications',
            'factures_libres'
        ),
        id=entreprise_id
    )
    
    # Services souscrits avec état
    services_souscrits = entreprise.services.annotate(
        progression=Case(
            When(demandes__statut='terminee', then=Value(100)),
            When(demandes__statut='en_cours', then=Value(50)),
            default=Value(0),
            output_field=IntegerField()
        )
    ).distinct()
    
    # Demandes groupées par statut
    demandes_par_statut = {
        'en_attente': entreprise.demandes.filter(statut='en_attente').select_related('service'),
        'acceptees': entreprise.demandes.filter(statut='acceptee').select_related('service'),
        'refusees': entreprise.demandes.filter(statut='refusee').select_related('service'),
        'en_cours': entreprise.demandes.filter(statut='en_cours').select_related('service'),
        'terminees': entreprise.demandes.filter(statut='terminee').select_related('service'),
    }
    
    # Factures groupées par statut
    factures_par_statut = {
        'envoyees': entreprise.factures_libres.filter(statut='envoyee').order_by('-date_envoi'),
        'recues': entreprise.factures_libres.filter(statut='reçue').order_by('-date_envoi'),
        'payees': entreprise.factures_libres.filter(statut='payee').order_by('-date_envoi'),
    }
    
    # Formulaires
    service_form = ServiceEntrepriseForm(request.POST or None, prefix='service')
    notification_form = NotificationEntrepriseForm(request.POST or None, request.FILES or None, prefix='notification')
    facture_form = FactureLibreForm(request.POST or None, request.FILES or None, prefix='facture')
    
    # Gestion des formulaires
    if request.method == 'POST':
        if 'add_service' in request.POST and service_form.is_valid():
            new_service = service_form.save(commit=False)
            new_service.entreprise = entreprise
            new_service.save()
            messages.success(request, "Service ajouté avec succès")
            return redirect('detail_entreprise', entreprise_id=entreprise.id)
            
        if 'send_notification' in request.POST and notification_form.is_valid():
            new_notification = notification_form.save(commit=False)
            new_notification.entreprise = entreprise
            new_notification.save()
            messages.success(request, "Notification envoyée avec succès")
            return redirect('detail_entreprise', entreprise_id=entreprise.id)
            
        if 'send_facture' in request.POST and facture_form.is_valid():
            new_facture = facture_form.save(commit=False)
            new_facture.entreprise = entreprise
            new_facture.envoyee_par = request.user
            new_facture.save()
            messages.success(request, "Facture envoyée avec succès")
            return redirect('detail_entreprise', entreprise_id=entreprise.id)
    
    context = {
        'entreprise': entreprise,
        'services_souscrits': services_souscrits,
        'demandes_par_statut': demandes_par_statut,
        'factures_par_statut': factures_par_statut,
        'notifications': entreprise.notifications.order_by('-date_envoi')[:10],
        'service_form': service_form,
        'notification_form': notification_form,
        'facture_form': facture_form,
        'stats': {
            'services_actifs': entreprise.services.filter(actif=True).count(),
            'demandes_en_attente': entreprise.demandes.filter(statut='en_attente').count(),
            'factures_impayees': entreprise.factures_libres.exclude(statut='payee').count(),
            'notifications_non_lues': entreprise.notifications.filter(lu=False).count(),
        }
    }
    
    return render(request, 'entreprise/backend/entreprise_detail.html', context)
#___________________________________________________________________________________
#

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
#___________________________________________________________________________________
#

@login_required
@user_passes_test(is_rh_or_admin)
def entreprises_en_attente(request):
    entreprises = User.objects.filter(  role='entreprise', is_active=False,  entreprise__isnull=False).select_related('entreprise')
    return render(request, 'entreprise/backend/entreprise_en_attente.html', {'entreprises': entreprises})

#___________________________________________________________________________________
#



@login_required
@user_passes_test(is_rh_or_admin)
def add_entreprise(request):
    if request.method == 'POST':
        form = CreateEntrepriseForm(request.POST, request.FILES)
        if form.is_valid():
            # 1. Création du User (sans mot de passe encore)
            user = form.save(commit=False)
            
            # 2. Génération du mot de passe
            password = 'passer123'
            user.set_password(password)
            user.is_active = True
            user.save()

            # 3. Création de l'Entreprise
            Entreprise.objects.create(
                user=user,
                nom=form.cleaned_data['nom'],
                secteur_activite=form.cleaned_data['secteur_activite'],
                site_web=form.cleaned_data.get('site_web'),
                description=form.cleaned_data.get('description'),
                adresse=form.cleaned_data.get('adresse'),
                ville=form.cleaned_data.get('ville'),
                pays=form.cleaned_data.get('pays'),
                taille_entreprise=form.cleaned_data.get('taille_entreprise'),
                logo=form.cleaned_data.get('logo'),
                accepte_cgv_cgu=True,
                date_acceptation_cgv_cgu=timezone.now(),
                statut='active',
                approuvee=True
            )

            # 4. Envoi de l'email avec identifiants
            send_mail(
                subject="Votre compte entreprise Antarès est créé",
                message=(
                    f"Bonjour {user.first_name},\n\n"
                    f"Votre compte entreprise a été créé avec succès.\n"
                    f"Voici vos identifiants de connexion :\n\n"
                    f"Email : {user.email}\n"
                    f"Mot de passe : {password}\n\n"
                    f"Veuillez vous connecter et changer votre mot de passe."
                ),
                from_email="noreply@antares-rh.test",
                recipient_list=[user.email],
                fail_silently=False,
            )

            messages.success(request, "Entreprise créée et email envoyé au représentant.")
            return redirect('entreprise-dashboard')
    else:
        form = CreateEntrepriseForm()

    return render(request, 'entreprise/backend/add_entreprise.html', {'form': form})
#___________________________________________________________________________________
#


@login_required
@user_passes_test(is_rh_or_admin)
def activite_recente(request):
    entreprises = Entreprise.objects.filter(approuvee=True).order_by('-date_inscription')[:10]
    return render(request, 'entreprise/backend/activite_recente.html', {'entreprises': entreprises})
#___________________________________________________________________________________
#

@login_required
@user_passes_test(is_rh_or_admin)
def corbeille_entreprises(request):
    entreprises = Entreprise.objects.filter(deleted=True).select_related('user', 'deleted_by')
    return render(request, 'entreprise/backend/corbeille.html', {'entreprises': entreprises})

#___________________________________________________________________________________
#



@login_required
@user_passes_test(is_rh_or_admin)
def approuver_entreprise(request, entreprise_id):
    entreprise = get_object_or_404(Entreprise, id=entreprise_id)
    user = entreprise.user

    # 1. Générer un mot de passe aléatoire
    new_password = get_random_string(length=10)
    user.set_password(new_password)

    # 2. Activer l’utilisateur
    user.is_active = True
    user.save()

    # 3. Marquer l’entreprise approuvée
    entreprise.approuvee = True
    entreprise.statut = 'active'
    entreprise.save()

    # 4. Envoyer l'email simulé
    subject = "Votre compte Antarès RH a été activé"
    message = (
        f"Bonjour {user.first_name},\n\n"
        f"Votre entreprise « {entreprise.nom} » a été approuvée.\n"
        f"Voici vos identifiants de connexion :\n\n"
        f"🔑 Email : {user.email}\n"
        f"🔒 Mot de passe : {new_password}\n\n"
        f"Veuillez vous connecter depuis http://localhost:8000/auth/login\n\n"
        f"Cordialement,\nL’équipe Antarès RH"
    )

    send_mail(subject, message, None, [user.email])

    messages.success(request, f"L'entreprise « {entreprise.nom} » a été approuvée et un email a été envoyé.")
    return redirect('entreprise-liste')
#___________________________________________________________________________________
#


@login_required
@user_passes_test(is_rh_or_admin)
def rejeter_entreprise(request, entreprise_id):
    entreprise = get_object_or_404(Entreprise, id=entreprise_id)

    entreprise.soft_delete(request.user)
    messages.success(request, f"L'entreprise {entreprise.nom} a été mise dans la corbeille.")
    
    return redirect('entreprise-liste')
#___________________________________________________________________________________
#

@login_required
@user_passes_test(is_rh_or_admin)
def restaurer_entreprise(request, entreprise_id):
    entreprise = get_object_or_404(Entreprise, id=entreprise_id, deleted=True)

    entreprise.user.is_active = True
    entreprise.user.save()

    entreprise.deleted = False
    entreprise.deleted_at = None
    entreprise.deleted_by = None
    entreprise.approuvee = True
    entreprise.statut = 'active'
    entreprise.save()

    messages.success(request, f"L'entreprise {entreprise.nom} a été restaurée.")
    return redirect('entreprise-detail', entreprise_id=entreprise.id)


#___________________________________________________________________________________
#

@login_required
@user_passes_test(is_rh_or_admin)
def entreprises_desactivees(request, entreprise_id):
    entreprise = get_object_or_404(Entreprise, id=entreprise_id)

    entreprise.approuvee = False
    entreprise.soft_delete(request.user, status='inactive')
    
    messages.success(request, "Le compte de l'entreprise a été désactivé.")
    return redirect('entreprise-detail', entreprise_id=entreprise.id)
#___________________________________________________________________________________
#


from django.utils.crypto import get_random_string
from django.utils.crypto import get_random_string

@login_required
@user_passes_test(is_rh_or_admin)
def reset_password_entreprise(request, entreprise_id):
    entreprise = get_object_or_404(Entreprise, id=entreprise_id)
    user = entreprise.user

    new_password = get_random_string(10)
    user.set_password(new_password)
    user.save()

    # Optionnel : send_mail(...)

    messages.success(request, f"Le mot de passe de {user.username} a été réinitialisé : {new_password}")
    return redirect('entreprise-detail', entreprise_id=entreprise.id)



#-------------------------------------------------------------------------------------
#                                       FRONTEND
#_____________________________________________________________________________________


def entreprise_right(user):
    return user.is_authenticated and user.role in ['entreprise']


@login_required
@user_passes_test(entreprise_right)
def dashboard_client(request):
    entreprise = get_object_or_404(Entreprise, user=request.user)
    
    context = {
        'entreprise': entreprise,
        'services_actifs': entreprise.services.filter(actif=True).annotate(
            nb_demandes=Count('demandes')
        ),
        'demandes_par_statut': {
            'en_attente': entreprise.demandes.filter(statut='en_attente'),
            'en_cours': entreprise.demandes.filter(statut='en_cours'),
            'terminees': entreprise.demandes.filter(statut='terminee'),
        },
        'notifications': entreprise.notifications.filter(lu=False).order_by('-date_envoi')[:5],
        'factures_impayees': entreprise.factures_libres.exclude(
            Q(statut='payee') | Q(statut='annulee'))
    }
    return render(request, 'entreprise/frontend/dashboard_client.html', context)

@login_required
@user_passes_test(entreprise_right)
def services_client(request):
    entreprise = get_object_or_404(Entreprise, user=request.user)
    services = entreprise.services.annotate(
        nb_demandes=Count('demandes', distinct=True),
        demandes_actives=Count('demandes', filter=Q(demandes__statut='en_cours'), distinct=True)
    )
    
    return render(request, 'entreprise/frontend/services_client.html', {
        'entreprise': entreprise,
        'services': services
    })

@login_required
@user_passes_test(entreprise_right)
def demandes_client(request):
    entreprise = get_object_or_404(Entreprise, user=request.user)
    
    statut = request.GET.get('statut', None)
    demandes = entreprise.demandes.select_related('service')
    
    if statut:
        demandes = demandes.filter(statut=statut)
    
    return render(request, 'entreprise/frontend/demandes_client.html', {
        'entreprise': entreprise,
        'demandes': demandes.order_by('-date_demande'),
        'filtre_statut': statut
    })