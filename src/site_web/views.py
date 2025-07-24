from django.shortcuts import render, redirect
from authentication.models import User

from django.contrib.auth.decorators import login_required
from django.contrib import messages

def home(request):
    return render(request, 'site_web/index.html')

def about(request):
    return render(request, 'site_web/about.html')

def services(request):
    return render(request, 'site_web/services.html')

def jobs(request):
    return render(request, 'site_web/jobs.html')

def contact(request):
    return render(request, 'site_web/contact.html')

def teams(request):
    return render(request, 'site_web/teams.html')

def appointment(request):
    return render(request, 'site_web/appointment.html')

def login(request):
    if request.method == 'GET' and 'from_registry' in request.GET:   
        return render(request, 'site_web/login.html', {'registration_success': True})
    # Traitement normal de la connexion
    return render(request, 'site_web/login.html')


def candidat_register(request):
    if request.method == 'POST':
        # Traitement de l'inscription
        return redirect('login?type=candidate&from_registry=true')
    return render(request, 'site_web/candidate_registry.html')


def recruteur_info(request):
    return render(request, 'site_web/recruteur_info.html')

def rejoindre_team(request):
    return render(request, 'site_web/rejoindre_team.html')



