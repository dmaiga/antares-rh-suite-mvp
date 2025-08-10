from django.shortcuts import render, redirect
from authentication.models import User

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from jobs.models import JobOffer
from django.shortcuts import render, get_object_or_404

#07_08

from django.core.paginator import Paginator
from django.db.models import Q


#09_08
from django.db.models import Q
from django.core.paginator import Paginator
from jobs.models import JobOffer, JobStatus

def jobs(request):
    # Récupération des paramètres
    search_query = request.GET.get('q', '')
    location = request.GET.get('location', '')
    sector = request.GET.get('sector', '')
    contract_type = request.GET.get('contract_type', '')
    hide_expired = request.GET.get('hide_expired', 'false') == 'true'
    page_number = request.GET.get('page', 1)
    
    # Filtrage de base
    jobs = JobOffer.objects.filter(
        visible_sur_site=True,
        statut__in=[JobStatus.OUVERT, JobStatus.EXPIRE]
    ).exclude(
        statut=JobStatus.BROUILLON
    ).order_by('-date_publication')
    #pour masque les offres expirées
    if hide_expired:
        jobs = jobs.exclude(statut=JobStatus.EXPIRE)
    
    # Filtres supplémentaires
    if search_query:
        jobs = jobs.filter(
            Q(titre__icontains=search_query) |
            Q(mission_principale__icontains=search_query) |
            Q(profil_recherche__icontains=search_query) |
            Q(societe__icontains=search_query)
        )
    
    if location:
        jobs = jobs.filter(lieu__icontains=location)
    
    if sector:
        jobs = jobs.filter(secteur__icontains=sector)
    
    if contract_type:
        jobs = jobs.filter(type_offre=contract_type)
    
    # Pagination - 10 éléments par page
    paginator = Paginator(jobs, 10)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'jobs': page_obj,
        'search_query': search_query,
        'location': location,
        'sector': sector,
        'contract_type': contract_type,
        'hide_expired': hide_expired,
        'status_choices': JobStatus.choices 
    }
    
    return render(request, 'site_web/public_jobs.html', context)

#
#_________________________________________________________________________________________________________________________
#

def public_job_offer_detail(request, pk):
    job = get_object_or_404(
        JobOffer, 
        pk=pk, 
        visible_sur_site=True,
        statut__in=['ouvert', 'expire'] 
    )
    
    # Suggestions d'autres offres
    related_jobs = JobOffer.objects.filter(
        visible_sur_site=True,
        statut='ouvert',
        secteur=job.secteur
    ).exclude(pk=pk).order_by('-date_publication')[:5]
    
    context = {
        'job': job,
        'related_jobs': related_jobs,
        'is_expired': job.statut == 'expire'
    }
    
    return render(request, 'site_web/public_job_detail.html', context)

#
#_________________________________________________________________________________________________________________________
#
def home(request):
    featured_jobs = JobOffer.objects.filter(
        visible_sur_site=True,
        statut__in=['ouvert', 'expire']
    ).order_by('-date_publication')[:6]
    
    context = {
        'featured_jobs': featured_jobs
    }
    
    return render(request, 'site_web/index.html', context)

#09_08 
#07_08
#______________________________________________________________________________
def about(request):
    return render(request, 'site_web/about.html')


def contact(request):
    return render(request, 'site_web/contact.html')

def teams(request):
    return render(request, 'site_web/teams.html')

def appointment(request):
    return render(request, 'site_web/appointment.html')

def login(request):
    login_type = request.GET.get('type', 'candidate')  # 'candidate' par défaut
    context = {'login_type': login_type}
    return render(request, 'site_web/login.html', context)

def candidat_register(request):
    if request.method == 'POST':
        # Traitement de l'inscription
        return redirect('login?type=candidate&from_registry=true')
    return render(request, 'site_web/candidate_registry.html')


def recruteur_info(request):
    return render(request, 'site_web/recruteur_info.html')

def rejoindre_team(request):
    return render(request, 'site_web/rejoindre_team.html')



