from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden

from .forms import JobOfferForm
from .models import JobOffer

def is_rh_or_admin(user):
    return user.is_authenticated and user.role in ['admin', 'rh']

# --- LISTE DES OFFRES ---
@login_required
@user_passes_test(is_rh_or_admin)
def job_offer_list(request):
    offers = JobOffer.objects.all().order_by('-date_publication')
    return render(request, 'jobs/job_offer_list.html', {'offers': offers})

# --- DETAIL D'UNE OFFRE ---
@login_required
@user_passes_test(is_rh_or_admin)
def job_offer_detail(request, pk):
    offer = get_object_or_404(JobOffer, pk=pk)
    return render(request, 'jobs/job_offer_detail.html', {'offer': offer})

# --- CREATION ---
@login_required
@user_passes_test(is_rh_or_admin)
def job_offer_create(request):
    if request.method == 'POST':
        form = JobOfferForm(request.POST, request.FILES)
        if form.is_valid():
            job_offer = form.save(commit=False)
            job_offer.auteur = request.user
            job_offer.save()
            return redirect('job-offer-detail', pk=job_offer.pk)
    else:
        form = JobOfferForm()
    return render(request, 'jobs/job_offer_form.html', {'form': form})

# --- MISE A JOUR ---
@login_required
@user_passes_test(is_rh_or_admin)
def job_offer_update(request, pk):
    job_offer = get_object_or_404(JobOffer, pk=pk)
    if request.method == 'POST':
        form = JobOfferForm(request.POST, request.FILES, instance=job_offer)
        if form.is_valid():
            form.save()
            return redirect('job-offer-detail', pk=job_offer.pk)
    else:
        form = JobOfferForm(instance=job_offer)
    return render(request, 'jobs/job_offer_form.html', {'form': form})

# --- SUPPRESSION ---
@login_required
@user_passes_test(is_rh_or_admin)
def job_offer_delete(request, pk):
    job_offer = get_object_or_404(JobOffer, pk=pk)
    if request.method == 'POST':
        job_offer.delete()
        return redirect('job-offer-list')
    return render(request, 'jobs/job_offer_confirm_delete.html', {'offer': job_offer})

# --- PUBLIER ---
@login_required
@user_passes_test(is_rh_or_admin)
def job_offer_publish(request, pk):
    job_offer = get_object_or_404(JobOffer, pk=pk)
    job_offer.statut = JobOffer.JobStatus.PUBLIE if hasattr(JobOffer, 'JobStatus') else 'publie'
    job_offer.visible_sur_site = True
    job_offer.save()
    return redirect('job-offer-detail', pk=pk)

# --- DE-PUBLIER ---
@login_required
@user_passes_test(is_rh_or_admin)
def job_offer_unpublish(request, pk):
    job_offer = get_object_or_404(JobOffer, pk=pk)
    job_offer.statut = JobOffer.JobStatus.BROUILLON if hasattr(JobOffer, 'JobStatus') else 'brouillon'
    job_offer.visible_sur_site = False
    job_offer.save()
    return redirect('job-offer-detail', pk=pk)
