
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from authentication.models import User
from .models import (
                        DemandeService,
                        NotificationEntreprise,
                        ServiceEntreprise,
                        ServiceRH,
                        
                    
                    )

from .forms import (EntrepriseRegisterForm,
                    CreateEntrepriseForm,
                    ServiceEntrepriseForm,
                      NotificationEntrepriseForm,
                     
                      DemandeServiceForm,
                      DemandeEditForm
                      )
                   
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
from django.db.models import Max, Count, Sum, Case, When, Value, IntegerField
from django.db.models.functions import Coalesce
from django.db.models import Prefetch
from django.utils import timezone
from .forms import ContrePropositionForm


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
            .filter(source='client')\
            .order_by('-date_envoi')[:5]
    
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
    services_a_traiter_count = ServiceEntreprise.objects.filter(
        entreprise=entreprise,
        statut='contre_proposition'
    ).count()
    
    # Récupérez une demande spécifique si nécessaire
    derniere_demande = entreprise.demandes.order_by('-date_demande').first()
    
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
        'demande': derniere_demande,
        'services_a_traiter_count': services_a_traiter_count,
        'services_souscrits': services_souscrits,
        'demandes_par_statut': demandes_par_statut,
        'factures_par_statut': factures_par_statut,
        'notifications': entreprise.notifications.order_by('-date_envoi')[:10],
        'service_form': service_form,
        'notification_form': notification_form,
        'facture_form': facture_form,
        'stats': {
            'services_actifs': entreprise.services.filter(statut='actif').count(),
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

#----------------------------------------------------------------------------------
#_________________________________________________________________________________
#__________________________________________________________________________________

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

@user_passes_test(is_rh_or_admin)
def generer_facture(request, service_id):
    service = get_object_or_404(ServiceEntreprise, id=service_id)
    
    if service.statut != 'accepte':
        messages.error(request, "Le service doit être accepté avant facturation")
        return redirect('gerer-statut-service', service_id=service.id)
    
    if request.method == 'POST':
        form = FactureLibreForm(request.POST, request.FILES, service=service)
        if form.is_valid():
            try:
                facture = form.save(commit=False)
                facture.entreprise = service.entreprise
                facture.service = service
                facture.envoyee_par = request.user
                facture.statut = 'a_payer'
                facture.date_envoi = timezone.now()
                
                # Génération automatique du PDF si aucun fichier fourni
                if not facture.fichier_facture:
                    facture.generer_pdf()
                
                facture.save()
                
                # Notification
                NotificationEntreprise.objects.create(
                    entreprise=service.entreprise,
                    service=service,
                    facture=facture,
                    titre=f"Nouvelle facture: {facture.titre}",
                    message=f"Une facture de {facture.montant_ttc} FCFA a été émise",
                    niveau='important',
                    action_requise=True
                )
                
                messages.success(request, f"Facture {facture.titre} générée avec succès")
                return redirect('detail-facture', facture_id=facture.id)
                
            except Exception as e:
                messages.error(request, f"Erreur lors de la génération: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = FactureLibreForm(service=service, initial={
            'titre': f"Facture {service.titre}",
            'description': f"Facture pour le service {service.titre}"
        })
    
    context = {
        'form': form,
        'service': service,
        'montant_ttc': service.prix * (1 + service.tva/100) if service else 0
    }
    return render(request, 'entreprise/factures/generer_facture.html', context)

from django.core.paginator import Paginator

from django.db.models import Q
from django.utils.dateparse import parse_date
@user_passes_test(is_rh_or_admin)
def gerer_statut_service(request, service_id):
    service = get_object_or_404(ServiceEntreprise, id=service_id)
    factures = FactureLibre.objects.filter(service=service).order_by('-date_envoi')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'changer_statut':
            statut = request.POST.get('statut')
            if statut in dict(ServiceEntreprise.STATUT_CHOICES):
                service.statut = statut
                
                if statut == 'actif':
                    service.date_activation = timezone.now()
                elif statut == 'termine':
                    service.date_expiration = timezone.now()
                
                service.save()
                messages.success(request, f"Statut mis à jour: {service.get_statut_display()}")
        
        elif action == 'generer_facture':
            form = FactureLibreForm(request.POST, request.FILES, service=service)
            if form.is_valid():
                facture = form.save(commit=False)
                facture.service = service
                facture.entreprise = service.entreprise
                facture.envoyee_par = request.user
                facture.save()
                
                messages.success(request, f"Facture {facture.titre} créée avec succès")
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        
        elif action == 'envoyer_notification':
            message = request.POST.get('message', '')
            if message:
                NotificationEntreprise.objects.create(
                    entreprise=service.entreprise,
                    service=service,
                    titre=f"Mise à jour du service {service.titre}",
                    message=message,
                    niveau='info',
                    action_requise=False,
                    source='backoffice'
                )
                messages.success(request, "Notification envoyée")
            else:
                messages.error(request, "Le message ne peut pas être vide")
        
        return redirect('gerer-statut-service', service_id=service.id)
    
    return render(request, 'entreprise/backend/gerer_statut_service.html', {
        'service': service,
        'statuts': ServiceEntreprise.STATUT_CHOICES,
        'factures': factures,
        'form_facture': FactureLibreForm(service=service),
        'form_notification': NotificationEntrepriseForm()
    })


#07_08
#----------------------------------------------------------------------------------
#06_08

@login_required
@user_passes_test(is_rh_or_admin)
def creer_proposition_financiere(request, service_id):
    service = get_object_or_404(ServiceEntreprise, id=service_id)
    
    if request.method == 'POST':
        form = ServiceEntrepriseForm(request.POST, instance=service)
        if form.is_valid():
            service = form.save(commit=False)
            service.statut = 'proposition'
            service.responsable_rh = request.user
            
            # Calcul automatique du TTC si seulement le HT est fourni
            if not service.prix and service.prix_ht:
                service.prix = service.prix_ht * (1 + service.tva/100)
            
            service.save()
            
            # Notification avec les détails financiers complets
            NotificationEntreprise.objects.create(
                entreprise=service.entreprise,
                service=service,
                titre=f"Proposition financière pour {service.titre}",
                message=(
                    f"Montant HT: {service.prix_ht} FCFA\n"
                    f"TVA ({service.tva}%): {service.prix_ht * service.tva/100} FCFA\n"
                    f"Montant TTC: {service.prix} FCFA"
                ),
                niveau='info',
                action_requise=True,
                source='backoffice'
            )
            
            messages.success(request, "Proposition envoyée avec détails TVA")
            return redirect('liste-demandes-client', entreprise_id=service.entreprise.id)
    else:
        form = ServiceEntrepriseForm(instance=service)
    
    return render(request, 'entreprise/backend/creer_proposition_financiere.html', {
        'form': form,
        'service': service
    })

#___________________________________________________________________________________
#
@login_required
@user_passes_test(is_rh_or_admin)
def liste_services_pour_traitement(request):
    services = ServiceEntreprise.objects.filter(
        statut='contre_proposition'
    ).select_related('entreprise')
    
    return render(request, 'entreprise/backend/liste_services_traitement.html', {
        'services': services
    })

@login_required
@user_passes_test(is_rh_or_admin)
def traiter_reponse_proposition(request, service_id):
    try:
        service = ServiceEntreprise.objects.get(id=service_id)
    except ServiceEntreprise.DoesNotExist:
        messages.error(request, "Le service demandé n'existe pas")
        return redirect('liste-services-traitement') 
    
    # Vérification supplémentaire que le service est bien en statut contre_proposition
    if service.statut != 'contre_proposition':
        messages.warning(request, "Cette proposition n'est pas en état de contre-proposition")
        return redirect('liste-demandes-client', entreprise_id=service.entreprise.id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'accepter_contre_proposition':
            service.statut = 'accepte'
            service.save()
            service.activer()
            
            NotificationEntreprise.objects.create(
                entreprise=service.entreprise,
                service=service,
                titre=f"Contre-proposition acceptée pour {service.titre}",
                message=f"Votre contre-proposition a été acceptée. Le service est maintenant actif.",
                niveau='success',
                action_requise=False,
                source='backoffice'
            )
            
            messages.success(request, "Contre-proposition acceptée et service activé")
            return redirect('liste-demandes-client', entreprise_id=service.entreprise.id)
            
        elif action == 'refuser_contre_proposition':
            service.statut = 'refuse'
            service.save()
            
            NotificationEntreprise.objects.create(
                entreprise=service.entreprise,
                service=service,
                titre=f"Contre-proposition refusée pour {service.titre}",
                message=f"Votre contre-proposition a été refusée. Le service ne sera pas activé.",
                niveau='warning',
                action_requise=False,
                source='backoffice'
            )
            
            messages.warning(request, "Contre-proposition refusée")
            return redirect('liste-demandes-client', entreprise_id=service.entreprise.id)
            
        elif action == 'nouvelle_proposition':
            return redirect('creer-proposition-financiere', service_id=service.id)
    
    return render(request, 'entreprise/backend/traiter_reponse_proposition.html', {
        'service': service
    })

#06_08
#__________________________________________________________________________________



@login_required
@user_passes_test(is_rh_or_admin)
def creer_service(request, demande_id):
    demande = get_object_or_404(DemandeService, id=demande_id)
    if request.method == 'POST':
        form = ServiceEntrepriseForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.demande_origine = demande
            service.save()
            messages.success(request, "Service créé et envoyé à l'entreprise")
            return redirect('entreprise-dashboard')
    else:
        form = ServiceEntrepriseForm(initial={
            'titre': demande.service.nom,
            'description': demande.message
        })
    return render(request, 'entreprise/backend/creer_service.html', {'form': form, 'demande': demande})
#___________________________________________________________________________________
#

@login_required
@user_passes_test(is_rh_or_admin)
def detail_demande_client(request, demande_id):
    demande = get_object_or_404(DemandeService, id=demande_id)
    
    context = {
        'demande': demande,
        'historique': demande.historique.all().order_by('-date'),
    }
    return render(request, 'entreprise/backend/detail_demande_client.html', context)
#___________________________________________________________________________________
#

@login_required
@user_passes_test(is_rh_or_admin)
def demande_client_edit(request, demande_id):
    demande = get_object_or_404(DemandeService, id=demande_id)
    
    if not demande.peut_etre_modifiee():
        messages.warning(request, "Cette demande ne peut plus être modifiée")
        return redirect('demande-client-detail', demande_id=demande.id)
    
    if request.method == 'POST':
        form = DemandeEditForm(request.POST, instance=demande)
        if form.is_valid():
            form.save()
            messages.success(request, "Demande mise à jour avec succès")
            return redirect('demande-client-detail', demande_id=demande.id)
    else:
        form = DemandeEditForm(instance=demande)
    
    return render(request, 'entreprise/backend/demande_client_edit.html', {
        'form': form,
        'demande': demande
    })

#___________________________________________________________________________________
#

@login_required
@user_passes_test(is_rh_or_admin)
def consulter_demande(request, demande_id):
    demande = get_object_or_404(DemandeService, id=demande_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        message = request.POST.get('message', '')
        
        if action == 'accepter' and demande.statut == 'en_attente':
            # Créer une proposition financière (ServiceEntreprise)
            service = ServiceEntreprise.creer_depuis_demande(demande)
            
            # Rediriger vers la page de création de proposition financière
            return redirect('creer-proposition-financiere', service_id=service.id)
            
        elif action == 'refuser' and demande.statut == 'en_attente':
            return redirect('refuser-demande-motif', demande_id=demande.id)
    
    return render(request, 'entreprise/backend/consulter_demande.html', {'demande': demande})
#___________________________________________________________________________________
#
@login_required
@user_passes_test(is_rh_or_admin)
def refuser_demande_motif(request, demande_id):
    demande = get_object_or_404(DemandeService, id=demande_id)

    if demande.statut != 'en_attente':
        messages.error(request, "Cette demande ne peut plus être modifiée")
        return redirect('toutes-demandes-rh')  # ou vers la liste souhaitée

    if request.method == 'POST':
        motif_refus = request.POST.get('message', '').strip()
        if not motif_refus:
            messages.error(request, "Veuillez indiquer un motif de refus")
            return render(request, 'entreprise/backend/motif_refus_demande.html', {'demande': demande})

        demande.statut = 'refusee'
        demande.save()

        NotificationEntreprise.objects.create(
            entreprise=demande.entreprise,
            titre="Demande refusée",
            message=f"Votre demande '{demande.service.nom}' a été refusée. Motif : {motif_refus}",
            niveau='danger',
            action_requise=True
        )

        messages.success(request, "La demande a été refusée avec succès")
        return redirect('toutes-demandes-rh')

    return render(request, 'entreprise/backend/motif_refus_demande.html', {'demande': demande})


@login_required
@user_passes_test(is_rh_or_admin)
def facture_libre_create(request, entreprise_id):
    entreprise = get_object_or_404(Entreprise, id=entreprise_id)
    
    if request.method == 'POST':
        form = FactureLibreForm(request.POST, request.FILES)
        if form.is_valid():
            facture = form.save(commit=False)
            facture.entreprise = entreprise
            facture.envoyee_par = request.user
            facture.save()
            
            # Envoyer une notification à l'entreprise
            NotificationEntreprise.objects.create(
                entreprise=entreprise,
                titre=f"Nouvelle facture disponible",
                message=f"Une nouvelle facture '{facture.titre}' est disponible dans votre espace.",
                niveau='info',
                fichier=facture.fichier_facture
            )
            
            messages.success(request, "La facture a été créée et envoyée à l'entreprise.")
            return redirect('liste-entreprises')
    else:
        form = FactureLibreForm()
    
    return render(request, 'entreprise/backend/facture_libre_create.html', {
        'form': form,
        'entreprise': entreprise
    })

#___________________________________________________________________________________
#
@login_required
@user_passes_test(is_rh_or_admin)
def liste_demandes_client(request, entreprise_id):
    entreprise = get_object_or_404(Entreprise, id=entreprise_id)
    demandes = DemandeService.objects.filter(entreprise=entreprise).order_by('-date_demande')
    context = {
        'demandes_en_attente': demandes.filter(statut='en_attente'),
        'demandes_acceptees': demandes.filter(statut='acceptee'),
        'demandes_refusees': demandes.filter(statut='refusee'),
        'demandes_en_cours': demandes.filter(statut='en_cours'),
    }
    return render(request, 'entreprise/backend/liste_demandes_client.html', context)
#___________________________________________________________________________________
#

#___________________________________________________________________________________
#

@login_required
@user_passes_test(is_rh_or_admin)
def creer_facture_libre(request, entreprise_id):
    entreprise = get_object_or_404(Entreprise, id=entreprise_id)
    
    if request.method == 'POST':
        form = FactureLibreForm(request.POST, request.FILES)
        if form.is_valid():
            facture = form.save(commit=False)
            facture.entreprise = entreprise
            facture.envoyee_par = request.user
            facture.save()
            
            # Envoyer une notification à l'entreprise
            NotificationEntreprise.objects.create(
                entreprise=entreprise,
                titre=f"Nouvelle facture disponible",
                message=f"Une nouvelle facture '{facture.titre}' est disponible dans votre espace.",
                niveau='info',
                fichier=facture.fichier_facture
            )
            
            messages.success(request, "La facture a été créée et envoyée à l'entreprise.")
            return redirect('liste-entreprises')
    else:
        form = FactureLibreForm()
    
    return render(request, 'entreprise/backend/creer_facture_libre.html', {
        'form': form,
        'entreprise': entreprise
    })

#___________________________________________________________________________________
#

@login_required
@user_passes_test(is_rh_or_admin)
def detail_service_client(request, service_id):
    service = get_object_or_404(ServiceEntreprise, id=service_id)

    if request.method == 'POST':
        if 'retour' in request.POST:
            return redirect('services-par-entreprise', entreprise_id=service.entreprise.id)

        form = ServiceEntrepriseForm(request.POST, instance=service)

        if form.is_valid():
            form.save()

            if 'envoyer' in request.POST:
                service.activer()
                facture = service.generer_facture()
                messages.success(request, "Service activé et facture générée.")
                return redirect('services-par-entreprise', entreprise_id=service.entreprise.id)

    else:
        form = ServiceEntrepriseForm(instance=service)

    return render(request, 'entreprise/backend/detail_service_client.html', {
        'service': service,
        'form': form
    })


#___________________________________________________________________________________
#

#___________________________________________________________________________________
#

@login_required
@user_passes_test(is_rh_or_admin)
def demande_client_accepter(request, pk):
    demande = get_object_or_404(DemandeService, pk=pk)

    if demande.statut != 'en_attente':
        messages.warning(request, "Cette demande a déjà été traitée.")
        return redirect('liste-demandes-client', entreprise_id=demande.entreprise.id)

    if request.method == 'POST':
        message_rh = request.POST.get('message', '')

        demande.statut = 'acceptee'
        demande.save()

        NotificationEntreprise.objects.create(
            entreprise=demande.entreprise,
            titre="Demande acceptée",
            message=f"Votre demande pour le service « {demande.service.nom} » a été acceptée. {message_rh}",
            niveau='success',
            action_requise=False
        )

        messages.success(request, "Demande acceptée et notification envoyée.")
        return redirect('liste-demandes-client', entreprise_id=demande.entreprise.id)

    # Si ce n’est pas un POST, rediriger proprement
    return redirect('liste-demandes-client', entreprise_id=demande.entreprise.id)

#___________________________________________________________________________________
#
from django.shortcuts import render

@login_required
@user_passes_test(is_rh_or_admin)
def demande_client_refuser(request, pk):
    demande = get_object_or_404(DemandeService, pk=pk)

    if demande.statut != 'en_attente':
        messages.error(request, "Cette demande ne peut plus être modifiée")
        return redirect('toutes-demandes-rh')

    if request.method == 'POST':
        motif_refus = request.POST.get('message', '').strip()
        if not motif_refus:
            messages.error(request, "Veuillez indiquer un motif de refus")
            return render(request, 'entreprise/motif_refus_demande.html', {'demande': demande})

        demande.statut = 'refusee'
        demande.save()

        NotificationEntreprise.objects.create(
            entreprise=demande.entreprise,
            titre="Votre demande a été refusée",
            message=f"Votre demande de service « {demande.service.nom} » a été refusée. Motif : {motif_refus}",
            niveau='danger',
            action_requise=True
        )

        messages.success(request, "La demande a été refusée avec succès")
        return redirect('toutes-demandes-rh')

    # Si GET : afficher le formulaire de refus
    return render(request, 'entreprise/motif_refus_demande.html', {'demande': demande})


#___________________________________________________________________________________
# 04_08_2025
#


@login_required
@user_passes_test(is_rh_or_admin)
def toutes_les_demandes_rh(request):
    demandes = DemandeService.objects.select_related('entreprise', 'service').all().order_by('-date_demande')
    
    nom_entreprise = request.GET.get('entreprise')
    statut = request.GET.get('statut')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    type_service = request.GET.get('type_service')

    if nom_entreprise:
        demandes = demandes.filter(entreprise__nom__icontains=nom_entreprise)

    if statut:
        demandes = demandes.filter(statut=statut)

    if date_debut:
        demandes = demandes.filter(date_demande__gte=parse_date(date_debut))
    
    if date_fin:
        demandes = demandes.filter(date_demande__lte=parse_date(date_fin))
    
    if type_service:
        demandes = demandes.filter(service__nom__icontains=type_service)

    context = {
        'demandes': demandes,
        'statuts': ['en_attente', 'acceptee', 'refusee', 'en_cours', 'terminee'],
    }
    return render(request, 'entreprise/backend/toutes_les_demandes_rh.html', context)

@login_required
@user_passes_test(is_rh_or_admin)
def liste_services_par_entreprise(request, entreprise_id):
    entreprise = get_object_or_404(Entreprise, id=entreprise_id)
    services = ServiceEntreprise.objects.filter(entreprise=entreprise)

    # Filtrage par statut
    statut = request.GET.get('statut')
    if statut:
        services = services.filter(statut=statut)

    # Tri et pagination
    services = services.select_related('entreprise', 'responsable_rh').prefetch_related('demandes')
    paginator = Paginator(services.order_by('-date_creation'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'entreprise/backend/services_liste.html', {
        'entreprise': entreprise,
        'page_obj': page_obj,
        'services': page_obj.object_list, 
        'statut_filtre': statut,
        'STATUT_CHOICES': ServiceEntreprise.STATUT_CHOICES,
    })


@login_required
@user_passes_test(is_rh_or_admin)  
def liste_toutes_factures(request):
    factures = FactureLibre.objects.all().order_by('-date_envoi')

    # Filtrage par statut facultatif via GET ?statut=
    statut = request.GET.get('statut')
    if statut in ['envoyee', 'reçue', 'payee']:
        factures = factures.filter(statut=statut)

    # Pagination (10 factures par page)
    paginator = Paginator(factures, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'statut_filtre': statut,
    }
    return render(request, 'entreprise/backend/factures_liste.html', context)

@login_required
@user_passes_test(is_rh_or_admin)
def liste_factures_par_entreprise(request, entreprise_id):
    entreprise = get_object_or_404(Entreprise, id=entreprise_id)
    factures = FactureLibre.objects.filter(entreprise=entreprise)

    # Filtrage par statut
    statut = request.GET.get('statut')
    if statut:
        factures = factures.filter(statut=statut)

    # Pagination
    paginator = Paginator(factures.order_by('-date_envoi'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'entreprise/backend/factures_liste_entreprise.html', {
        'entreprise': entreprise,
        'page_obj': page_obj,
        'statut_filtre': statut,
    })


@login_required
@user_passes_test(is_rh_or_admin)  
def liste_notifications(request):
    notifications = NotificationEntreprise.objects.all().order_by('-date_envoi')

    # Pagination (10 par page)
    paginator = Paginator(notifications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'entreprise/backend/notifications_liste.html', {
        'page_obj': page_obj,
    })


@login_required
@user_passes_test(is_rh_or_admin)
def liste_notifications_par_entreprise(request, entreprise_id):
    entreprise = get_object_or_404(Entreprise, id=entreprise_id)
    notifications = NotificationEntreprise.objects.filter(entreprise=entreprise)

    # Filtrage par niveau
    niveau = request.GET.get('niveau')
    if niveau:
        notifications = notifications.filter(niveau=niveau)

    # Filtrage par lecture
    lu = request.GET.get('lu')
    if lu == 'oui':
        notifications = notifications.filter(lu=True)
    elif lu == 'non':
        notifications = notifications.filter(lu=False)

    # Pagination
    paginator = Paginator(notifications.order_by('-date_envoi'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'entreprise/backend/notification_liste_entreprise.html', {
        'entreprise': entreprise,
        'page_obj': page_obj,
        'niveau_filtre': niveau,
        'lu_filtre': lu,
    })


from django.shortcuts import render, get_object_or_404
from .models import FactureLibre

@login_required
@user_passes_test(is_rh_or_admin)
def facture_detail(request, facture_id):
    facture = get_object_or_404(FactureLibre, id=facture_id)

    if request.method == 'POST' and not facture.envoyee:
        # Logique d’envoi réelle ici (email, stockage, etc.)
        facture.envoyee = True
        facture.date_envoi = timezone.now()
        facture.save()

        messages.success(request, "📨 Facture envoyée avec succès.")
        return redirect('services-par-entreprise', entreprise_id=facture.entreprise.id)

    return render(request, 'entreprise/backend/facture_detail.html', {'facture': facture})



def notification_detail(request, notification_id):
    notification = get_object_or_404(NotificationEntreprise, id=notification_id)
    return render(request, 'notifications/detail.html', {'notification': notification})



#___________________________________________________________________________________
# 05_08_2025
#


def traiter_demande(request, pk):
    demande = get_object_or_404(DemandeService, pk=pk)

    if request.method == 'POST':
        form = DemandeEditForm(request.POST, instance=demande)
        if form.is_valid():
            form.save()
            # Proposer un service ?
            if 'proposer_service' in request.POST:
                ServiceEntreprise.creer_depuis_demande(demande)
                messages.success(request, "Service personnalisé créé à partir de la demande.")
            return redirect('liste_demandes')
    else:
        form = DemandeEditForm(instance=demande)

    return render(request, 'entreprise/backend/traiter_demande.html', {'form': form, 'demande': demande})

#-------------------------------------------------------------------------------------
#                                       FRONTEND
#_____________________________________________________________________________________





# Fonction utilitaire pour vérifier les droits entreprise
def entreprise_right(user):
    return user.is_authenticated and user.role in ['entreprise']

def get_entreprise_user(request):
    return request.user.entreprise

#--------------------------------------------------------------------------------------------------------
#05_08_2025

@login_required
@user_passes_test(entreprise_right)
def liste_propositions_services(request):
    entreprise = get_entreprise_user(request)
    services = ServiceEntreprise.objects.filter(
        entreprise=entreprise,
        statut__in=['proposition', 'en_revue']
    ).prefetch_related('demandes').order_by('-date_creation')

    return render(request, 'entreprise/frontend/suivi_demande_client.html', {
        'services': services,
    })


@login_required
@user_passes_test(entreprise_right)
def detail_demande_service(request, demande_id):
    entreprise = get_entreprise_user(request)
    demande = get_object_or_404(DemandeService, pk=demande_id, entreprise=entreprise)
    services = ServiceEntreprise.objects.filter(demandes=demande).order_by('date_creation')

    if request.method == "POST":
        service_id = request.POST.get("service_id")
        action = request.POST.get("action")
        reponse = request.POST.get("reponse")

        service = get_object_or_404(ServiceEntreprise, id=service_id, entreprise=entreprise)

        if action == "accepter":
            service.statut = "accepte"
            service.reponse_entreprise = reponse or ''
            service.save()
        elif action == "contre_proposition":
            # Créer une nouvelle contreproposition à partir du service original
            nouveau_service = ServiceEntreprise.objects.create(
                entreprise=entreprise,
                titre=service.titre,
                description=service.description,
                conditions=service.conditions,
                prix=service.prix,
                tva=service.tva,
                periodicite_facturation=service.periodicite_facturation,
                statut='contre_proposition',
                reponse_entreprise=reponse or '',
                responsable_rh=service.responsable_rh,
            )
            nouveau_service.demandes.set(service.demandes.all())

        return redirect('dashboard-client')

    return render(request, 'entreprise/frontend/suivi_demande_detail.html', {
        'demande': demande,
        'services': services,
    })

#-----------------------------------------------------------------------------------------------------------------
#06_08


@login_required
@user_passes_test(entreprise_right)
def accepter_proposition_service(request, service_id):
    service = get_object_or_404(ServiceEntreprise, id=service_id, entreprise=request.user.entreprise)

    if service.statut == 'proposition':
        service.accepter_proposition()
        messages.success(request, "Proposition acceptée. Le service sera activé.")
    else:
        messages.warning(request, "Action non autorisée sur ce statut de service.")

    return redirect('dashboard-client')

@login_required
@user_passes_test(entreprise_right)
def contre_proposition_service(request, service_id):
    service = get_object_or_404(ServiceEntreprise, id=service_id, entreprise=request.user.entreprise)

    if request.method == 'POST':
        form = ContrePropositionForm(request.POST, instance=service)
        if form.is_valid():
            service = form.save(commit=False)
            service.soumettre_contre_proposition(form.cleaned_data['contre_proposition'])
            messages.success(request, "Contre-proposition envoyée à l'équipe RH.")
            return redirect('liste-services-entreprise')
    else:
        form = ContrePropositionForm(instance=service)

    return render(request, 'entreprise/frontend/contre_proposition_form.html', {
        'form': form,
        'service': service
    })


#06_08
#____________________________________________________________________________________________________________________________

@login_required
@user_passes_test(entreprise_right)
def liste_services_entreprise(request):
    entreprise = get_entreprise_user(request)
    services = ServiceEntreprise.objects.filter(
        entreprise=entreprise
    ).exclude(statut__in=['proposition', 'en_revue', 'rejete'])  # filtrer que les actifs / en cours

    return render(request, 'entreprise/frontend/suivi_services.html', {
        'services': services
    })

#05_08_2025
#_______________________________________________________________________________________________________________

# Vues principales
@login_required
@user_passes_test(entreprise_right)
def dashboard_client(request):
    entreprise = get_object_or_404(Entreprise, user=request.user)
    
    context = {
        'entreprise': entreprise,
        'services_actifs': entreprise.services.filter(statut='actif').annotate(
            nb_demandes=Count('demandes')
        ),
        'demandes_par_statut': {
            'en_attente': entreprise.demandes.filter(statut='en_attente').count(),
            'en_cours': entreprise.demandes.filter(statut='en_cours').count(),
            'terminees': entreprise.demandes.filter(statut='terminee').count(),
        },
        'notifications': entreprise.notifications.filter(lu=False).order_by('-date_envoi')[:5],
        'factures_impayees': entreprise.factures_libres.exclude(
            Q(statut='payee') | Q(statut='annulee')).count(),
        'demandes_recentes': entreprise.demandes.order_by('-date_demande')[:5]
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

# Vues pour les demandes de service
@login_required
@user_passes_test(entreprise_right)
def demandes_client(request):
    entreprise = get_object_or_404(Entreprise, user=request.user)
    
    statut = request.GET.get('statut')
    demandes = entreprise.demandes.select_related('service')
    
    if statut:
        demandes = demandes.filter(statut=statut)
    
    return render(request, 'entreprise/frontend/demandes_client.html', {
        'entreprise': entreprise,
        'demandes': demandes.order_by('-date_demande'),
        'filtre_statut': statut
    })

@login_required
@user_passes_test(entreprise_right)
def demander_service(request):
    entreprise = get_object_or_404(Entreprise, user=request.user)
    
    if request.method == 'POST':
        form = DemandeServiceForm(request.POST, request.FILES)
        if form.is_valid():
            demande = form.save(commit=False)
            demande.entreprise = entreprise
            demande.statut = 'en_attente'
            demande.save()
            messages.success(request, "Demande envoyée avec succès")
            return redirect('demandes-client')
    else:
        form = DemandeServiceForm()
    
    return render(request, 'entreprise/frontend/demander_service.html', {
        'form': form
    })

@login_required
@user_passes_test(entreprise_right)
def annuler_demande(request, demande_id):
    demande = get_object_or_404(DemandeService, id=demande_id, entreprise__user=request.user)
    
    if not demande.peut_etre_annulee():
        messages.error(request, "Cette demande ne peut plus être annulée.")
        return redirect('demandes-client')
    
    if request.method == 'POST':
        demande.delete()
        messages.success(request, "La demande a été annulée avec succès.")
        return redirect('demandes-client')
    
    return render(request, 'entreprise/frontend/confirmation_annulation.html', {
        'demande': demande
    })

# Vues pour les factures
@login_required
@user_passes_test(entreprise_right)
def factures_client(request):
    entreprise = get_object_or_404(Entreprise, user=request.user)
    statut = request.GET.get('statut')
    
    factures = entreprise.factures_libres.all()
    if statut:
        factures = factures.filter(statut=statut)
    
    return render(request, 'entreprise/frontend/factures_client.html', {
        'factures': factures.order_by('-date_envoi'),
        'filtre_statut': statut
    })

@login_required
@user_passes_test(entreprise_right)
def upload_preuve_paiement(request, facture_id):
    facture = get_object_or_404(FactureLibre, id=facture_id, entreprise__user=request.user)
    
    if request.method == 'POST' and 'preuve_paiement' in request.FILES:
        facture.preuve_paiement = request.FILES['preuve_paiement']
        facture.statut = 'payee'
        facture.save()
        messages.success(request, "La preuve de paiement a été envoyée.")
        return redirect('factures-client')
    
    return render(request, 'entreprise/frontend/upload_preuve.html', {
        'facture': facture
    })

# Vues pour les notifications
@login_required
@user_passes_test(entreprise_right)
def notifications_client(request):
    entreprise = get_object_or_404(Entreprise, user=request.user)
    
    notifications = entreprise.notifications.all().order_by('-date_envoi')
    non_lues = notifications.filter(lu=False)
    
    if request.method == 'POST':
        # Marquer toutes les notifications comme lues
        non_lues.update(lu=True)
        messages.success(request, "Toutes les notifications ont été marquées comme lues.")
        return redirect('notifications-client')
    
    return render(request, 'entreprise/frontend/notifications_client.html', {
        'notifications': notifications,
        'nombre_non_lues': non_lues.count()
    })

@login_required
@user_passes_test(entreprise_right)
def envoyer_notification(request, entreprise_id):
    entreprise = get_object_or_404(Entreprise, id=entreprise_id)
    
    if request.method == 'POST':
        form = NotificationEntrepriseForm(request.POST, request.FILES)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.entreprise = entreprise
            notification.envoyee_par = request.user
            notification.save()
            
            messages.success(request, "La notification a été envoyée avec succès.")
            return redirect('consulter-demande', demande_id=request.GET.get('demande_id'))
    else:
        initial = {}
        if 'demande_id' in request.GET:
            demande = get_object_or_404(DemandeService, id=request.GET['demande_id'])
            initial['titre'] = f"Re: Demande #{demande.id} - {demande.service.nom}"
        
        form = NotificationEntrepriseForm(initial=initial)
    
    context = {
        'form': form,
        'entreprise': entreprise,
        'demande_id': request.GET.get('demande_id')
    }
    return render(request, 'entreprise/backend/envoyer_notification.html', context)

@login_required
@user_passes_test(entreprise_right)
def modifier_service(request, service_id):
    entreprise = get_object_or_404(Entreprise, user=request.user)
    service = get_object_or_404(ServiceEntreprise, id=service_id, entreprise=entreprise)
    
    if request.method == 'POST':
        form = ServiceEntrepriseForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "Service modifié avec succès.")
            return redirect('services-client')
    else:
        form = ServiceEntrepriseForm(instance=service)
    
    return render(request, 'entreprise/frontend/modifier_service.html', {
        'form': form,
        'service': service
    })

@login_required
@user_passes_test(entreprise_right)
def toggle_service(request, service_id):
    entreprise = get_object_or_404(Entreprise, user=request.user)
    service = get_object_or_404(ServiceEntreprise, id=service_id, entreprise=entreprise)
    
    service.actif = not service.actif
    service.save()
    
    status = "activé" if service.actif else "désactivé"
    messages.success(request, f"Le service a été {status} avec succès.")
    return redirect('services-client')

# Vue pour le catalogue des services RH
@login_required
@user_passes_test(entreprise_right)
def catalogue_services(request):
    services = ServiceRH.objects.annotate(
        entreprises_utilisatrices=Count('demandeservice__entreprise', distinct=True)
    )
    return render(request, 'entreprise/frontend/catalogue_services.html', {
        'services': services
    })