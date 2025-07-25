from django.shortcuts import render, redirect
from authentication.models import User

from django.contrib.auth.decorators import login_required
from django.contrib import messages

def home(request):
    return render(request, 'site_web/index.html')

def about(request):
    return render(request, 'site_web/about.html')


def jobs(request):
    return render(request, 'site_web/jobs.html')

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



