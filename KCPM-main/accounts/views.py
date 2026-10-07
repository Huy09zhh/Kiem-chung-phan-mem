from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .forms import RegisterForm, LoginForm, ProfileUpdateForm, CustomPasswordChangeForm
from .decorators import admin_required


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    next_url = request.GET.get('next') or request.POST.get('next') or 'home'
    form = RegisterForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect(next_url)

    return render(request, 'accounts/register.html', {
        'form': form,
        'next': next_url,
    })


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('home')

    next_url = request.GET.get('next') or request.POST.get('next') or 'home'
    form = LoginForm(request, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)

        if user.is_staff:
            return redirect('admin_dashboard')

        return redirect(next_url)

    return render(request, 'accounts/login.html', {
        'form': form,
        'next': next_url,
    })


@require_POST
@login_required(login_url='login')
def logout_view(request):
    logout(request)
    return redirect('home')


@login_required(login_url='login')
def profile_view(request):
    return render(request, 'accounts/profile.html')


@login_required(login_url='login')
def profile_update_view(request):
    form = ProfileUpdateForm(request.POST or None, instance=request.user)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('profile')

    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required(login_url='login')
def change_password_view(request):
    form = CustomPasswordChangeForm(request.user, request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        return redirect('profile')

    return render(request, 'accounts/change_password.html', {'form': form})

@admin_required
def admin_dashboard_view(request):
    return render(request, 'admin_panel/dashboard.html')