from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .forms import RegisterForm, LoginForm, ProfileUpdateForm, UserProfileUpdateForm, CustomPasswordChangeForm
from .decorators import admin_required


def get_safe_next_url(request, default='home'):
    """Chỉ chấp nhận next là đường dẫn nội bộ của Green Shop (chống Open Redirect)."""
    next_url = request.POST.get('next') or request.GET.get('next') or ''
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return default


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    next_url = get_safe_next_url(request)
    form = RegisterForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
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

    next_url = get_safe_next_url(request)
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
    # SCRUM-30: Dùng UserProfileUpdateForm — form này không có trường username,
    # nên dữ liệu username từ POST sẽ không bao giờ được xử lý hay lưu.
    form = UserProfileUpdateForm(request.POST or None, instance=request.user)

    if request.method == 'POST' and form.is_valid():
        # Defense-in-depth: lưu commit=False để kiểm tra lại username trước khi save.
        user_instance = form.save(commit=False)
        # Luôn khôi phục username về giá trị ban đầu, đề phòng mọi trường hợp.
        user_instance.username = request.user.username
        user_instance.save()
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
