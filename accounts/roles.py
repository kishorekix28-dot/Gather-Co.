"""Role helpers: ADMIN has full access, STAFF has operational access, CUSTOMER can book items."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

ADMIN = "ADMIN"
STAFF = "STAFF"
CUSTOMER = "CUSTOMER"


def get_role(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return ADMIN
    profile = getattr(user, "profile", None)
    return profile.role if profile else CUSTOMER


def is_admin(user):
    return get_role(user) == ADMIN


def is_staff_member(user):
    """Staff and administrators operate the inventory."""
    return get_role(user) in (ADMIN, STAFF)


def is_customer(user):
    return get_role(user) == CUSTOMER


def staff_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_staff_member(request.user):
            raise PermissionDenied("Staff access is required.")
        return view_func(request, *args, **kwargs)

    return wrapper


def customer_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_customer(request.user):
            raise PermissionDenied("This page is for customer accounts.")
        return view_func(request, *args, **kwargs)

    return wrapper


def admin_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied("Administrator access is required.")
        return view_func(request, *args, **kwargs)

    return wrapper


class AdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not is_admin(request.user):
            raise PermissionDenied("Administrator access is required.")
        return super().dispatch(request, *args, **kwargs)
