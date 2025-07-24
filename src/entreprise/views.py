
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
    user = get_object_or_404(User, id=user_id, role='entreprise', is_active=False)
    # 1. Activer le compte utilisateur
    user.is_active = True
    user.save()
    # 2. Marquer l'entreprise comme approuvée
    if hasattr(user, 'entreprise'):
        user.entreprise.approuvee = True
        user.entreprise.save()

    # 3. Envoyer un e-mail avec identifiants (exemple simple, peut être amélioré)
    # send_mail(
    #     subject="Compte entreprise validé",
    #     message=f"Bonjour {user.username}, votre compte a été validé. Vous pouvez vous connecter avec vos identifiants.",
    #     from_email="noreply@antares.com",
    #     recipient_list=[user.email],
    # )

    messages.success(request, f"L'entreprise « {user.entreprise.nom} » a été validée.")
    return redirect('entreprise-dashboard')


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
            messages.success(request, "Votre demande d'inscription a été enregistrée avec succès. Notre équipe va l'examiner et vous contactera sous peu.")
            return redirect('confirmation-inscription')
    else:
        form = EntrepriseRegisterForm()

    return render(request, 'entreprise/entreprise_registry.html', {'form': form})

def entreprise_info(request):
    return render(request, 'entreprise/entreprise_info.html')

def savoir_plus(request):
    return render(request, 'entreprise/savoir_plus.html')

def confirmation_inscription(request):
    return render(request, 'entreprise/confirmation_inscription.html')


@login_required
@user_passes_test(is_rh_or_admin)
def entreprise_liste(request):
    entreprises_list = User.objects.filter(role='entreprise')
    paginator = Paginator(entreprises_list, 25)  # 25 entreprises par page
    
    page_number = request.GET.get('page')
    entreprises = paginator.get_page(page_number)
    
    return render(request, 'entreprise/entreprise_liste.html', {'entreprises': entreprises})
@login_required
@user_passes_test(is_rh_or_admin)
def entreprises_actives(request):
    entreprises = Entreprise.objects.filter(approuvee=True)
    return render(request, 'entreprise/entreprise_actives.html', {'entreprises': entreprises})

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
        entreprise = user.entreprise  # grâce au related_name='entreprise'
        entreprise.delete()
    except Entreprise.DoesNotExist:
        pass  # si jamais il n'y a pas de modèle entreprise

    user.delete()

    messages.info(request, f"L'entreprise {user.username} a été rejetée et supprimée.")
    return redirect('entreprise-en-attente')
