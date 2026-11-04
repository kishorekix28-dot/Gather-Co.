from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from inventory.services import log_activity

from .forms import LoginForm, RegistrationForm, StyledPasswordChangeForm, UserRoleForm
from .models import Profile
from .roles import STAFF, admin_required


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    http_method_names = ["post", "options"]


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("inventory:dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        Profile.objects.update_or_create(user=user, defaults={"role": STAFF})
        login(request, user)
        log_activity(user, "Registered", f"New staff account {user.username}")
        messages.success(request, "Welcome! Your staff account has been created.")
        return redirect("inventory:dashboard")
    return render(request, "accounts/register.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    form = StyledPasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been changed.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})


@admin_required
def user_list(request):
    q = request.GET.get("q", "").strip()
    users = User.objects.select_related("profile").order_by("username")
    if q:
        users = users.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q))
    page = Paginator(users, 15).get_page(request.GET.get("page"))
    return render(request, "accounts/user_list.html", {"page_obj": page, "q": q})


@admin_required
@require_http_methods(["GET", "POST"])
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    profile_obj, _ = Profile.objects.get_or_create(user=user)
    form = UserRoleForm(request.POST or None, instance=profile_obj)
    if request.method == "POST" and form.is_valid():
        if user == request.user and (form.cleaned_data["role"] != "ADMIN" or not form.cleaned_data["is_active"]):
            messages.error(request, "You cannot remove your own administrator access.")
        else:
            form.save()
            log_activity(request.user, "Updated user", f"{user.username} → {profile_obj.get_role_display()}")
            messages.success(request, f"User {user.username} updated.")
            return redirect("accounts:user_list")
    return render(request, "accounts/user_form.html", {"form": form, "target": user})
