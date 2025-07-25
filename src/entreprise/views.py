
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from authentication.models import User
from .forms import EntrepriseRegisterForm
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
from django.db.models import Count, Q
from django.db.models import ExpressionWrapper, F, FloatField
from django.db.models import Case, When, IntegerField, Value, Sum

def is_rh_or_admin(user):
    return user.is_authenticated and user.role in ['admin', 'rh']


@login_required
@user_passes_test(is_rh_or_admin)
def dashboard_rh(request):
    stats = {
        'total_entreprises': Entreprise.objects.count(),
        'entreprises_actives': Entreprise.objects.filter(approuvee=True).count(),
        'entreprises_en_attente': Entreprise.objects.filter(user__is_active=False).count(),
        'derniere_validation': Entreprise.objects.filter(approuvee=True)
                              .order_by('-date_inscription')
                              .first().date_inscription if Entreprise.objects.filter(approuvee=True).exists() else "Jamais"
    }

    entreprises_en_attente = Entreprise.objects.filter(user__is_active=False).select_related('user').order_by('-user__date_joined')[:10]
    dernieres_validees = Entreprise.objects.filter(user__is_active=True).select_related('user').order_by('-user__date_joined')[:3]

    context = {
        'stats': stats,
        'entreprises_en_attente': entreprises_en_attente,
        'dernieres_validees': dernieres_validees,
        'entreprises_corbeille': Entreprise.objects.filter(deleted=True).count(),
    }
    return render(request, 'entreprise/entreprise_dashboard.html', context)


@login_required
@user_passes_test(is_rh_or_admin)
def entreprises_en_attente(request):
    entreprises = User.objects.filter(  role='entreprise', is_active=False,  entreprise__isnull=False).select_related('entreprise')
    return render(request, 'entreprise/entreprise_en_attente.html', {'entreprises': entreprises})

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
    except User.DoesNotExist:
        raise Http404("Aucun utilisateur entreprise ne correspond à cet identifiant.")

    entreprise = user.entreprise

    return render(request, 'entreprise/entreprise_detail.html', {'entreprise': entreprise})

def entreprise_registry(request):
    if request.method == 'POST':
        form = EntrepriseRegisterForm(request.POST)
        if form.is_valid():
            form.save()  # L'objet User ET Entreprise sont créés ici
            return redirect('confirmation-inscription')
    else:
        form = EntrepriseRegisterForm()

    return render(request, 'entreprise/entreprise_registry.html', {'form': form})

def add_entreprise(request):
    if request.method == 'POST':
        form = EntrepriseRegisterForm(request.POST)
        if form.is_valid():
            form.save()  # L'objet User ET Entreprise sont créés ici
            return redirect('entreprise-dashboard')
    else:
        form = EntrepriseRegisterForm()

    return render(request, 'entreprise/add_entreprise.html', {'form': form})

def entreprise_info(request):
    return render(request, 'entreprise/entreprise_info.html')

def savoir_plus(request):
    return render(request, 'entreprise/savoir_plus.html')

def confirmation_inscription(request):
    return render(request, 'entreprise/confirmation_inscription.html')

def services(request):
    return render(request, 'entreprise/services.html')


@login_required
@user_passes_test(is_rh_or_admin)
def entreprise_liste(request):
    # Récupération des paramètres de filtrage
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    sort_by = request.GET.get('sort', '-date_inscription')

    # Construction de la requête de base avec select_related pour optimiser
    queryset = Entreprise.objects.filter(deleted=False).select_related('user').all()
    # Application des filtres
    if search_query:
        queryset = queryset.filter(
            Q(nom__icontains=search_query) |
            Q(secteur_activite__icontains=search_query) |
            Q(ville__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )

    if status_filter:
        if status_filter == 'active':
            queryset = queryset.filter(statut='active')
        elif status_filter == 'inactive':
            queryset = queryset.filter(statut='non_active')
        elif status_filter == 'pending':
            queryset = queryset.filter(approuvee=False)
        elif status_filter == 'pause':
            queryset = queryset.filter(statut='pause')

    # Gestion du tri
    sort_mapping = {
        '-date_joined': '-user__date_joined',
        'date_joined': 'user__date_joined',
        '-nom': '-nom',
        'nom': 'nom',
        '-date_inscription': '-date_inscription',
        'date_inscription': 'date_inscription'
    }
    
    # Utilisation du mapping avec une valeur par défaut
    sort_field = sort_mapping.get(sort_by, '-date_inscription')
    queryset = queryset.order_by(sort_field)

    # Pagination
    paginator = Paginator(queryset, 25)  # 25 entreprises par page
    page = request.GET.get('page')

    try:
        entreprises = paginator.page(page)
    except PageNotAnInteger:
        entreprises = paginator.page(1)
    except EmptyPage:
        entreprises = paginator.page(paginator.num_pages)

    context = {
        'entreprises': entreprises,
        'page_range': paginator.get_elided_page_range(number=entreprises.number, on_each_side=2, on_ends=1),
    }
    return render(request, 'entreprise/entreprise_liste.html', context)



@login_required
@user_passes_test(is_rh_or_admin)
def entreprises_actives(request):
    # Définir les périodes de référence
    one_week_ago = timezone.now() - timezone.timedelta(days=7)
    one_month_ago = timezone.now() - timezone.timedelta(days=30)
    
    # Filtrer les entreprises actives (non supprimées)
    entreprises = Entreprise.objects.filter(
        approuvee=True,
        deleted=False
    ).select_related('user')
    
    # Calculer les statistiques
    stats = {
        'total_actives': entreprises.count(),
        'new_this_week': entreprises.filter(date_inscription__gte=one_week_ago).count(),
        'recent_logins': entreprises.filter(user__last_login__gte=one_week_ago).count(),
        'inactive_over_month': entreprises.filter(
            Q(user__last_login__lt=one_month_ago) | Q(user__last_login__isnull=True)
        ).count(),
        'complete_profiles': entreprises.filter(
            Q(ville__isnull=False) & 
            Q(pays__isnull=False) & 
            Q(secteur_activite__isnull=False) &
            Q(description__isnull=False)
        ).count(),
    }
    
    # Ajouter des annotations pour la complétude du profil
    entreprises = entreprises.annotate(
        profile_fields_filled=(
            Case(When(ville__isnull=False, then=Value(1)), default=Value(0)) +
            Case(When(pays__isnull=False, then=Value(1)), default=Value(0)) +
            Case(When(secteur_activite__isnull=False, then=Value(1)), default=Value(0)) +
            Case(When(description__isnull=False, then=Value(1)), default=Value(0))
        )
    ).annotate(
        profile_completion_percent=ExpressionWrapper(  # Changed name here
            F('profile_fields_filled') * 25, 
            output_field=IntegerField()
        )
    )
    paginator = Paginator(entreprises, 25)  # 25 entreprises par page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'entreprises': entreprises,
        'stats': stats,
        'one_week_ago': one_week_ago,
        'one_month_ago': one_month_ago,
    }
    return render(request, 'entreprise/entreprise_actives.html', context)


@login_required
@user_passes_test(is_rh_or_admin)
def activite_recente(request):
    entreprises = Entreprise.objects.filter(approuvee=True).order_by('-date_inscription')[:10]
    return render(request, 'entreprise/activite_recente.html', {'entreprises': entreprises})


@login_required
@user_passes_test(is_rh_or_admin)
def entreprises_desactivees(request, user_id):
    user = get_object_or_404(User, id=user_id, role='entreprise')
    entreprise = get_object_or_404(Entreprise, user=user)

    entreprise.approuvee = False
    entreprise.statut = 'terminee'
    user.is_active = False

    user.save()
    entreprise.save()
    
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
    return render(request, 'entreprise/corbeille.html', {'entreprises': entreprises})

@login_required
@user_passes_test(is_rh_or_admin)
def restaurer_entreprise(request, entreprise_id):
    entreprise = get_object_or_404(Entreprise, id=entreprise_id, deleted=True)
    
    entreprise.deleted = False
    entreprise.deleted_at = None
    entreprise.deleted_by = None
    entreprise.save()
    
    # Réactiver aussi le compte utilisateur associé
    entreprise.user.is_active = True
    entreprise.user.save()
    
    messages.success(request, f"L'entreprise {entreprise.nom} a été restaurée.")
    return redirect('corbeille-entreprises')