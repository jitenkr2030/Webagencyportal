"""Access control for the client portal and the staff console."""
from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .models import ClientProfile


def safe_next(request, default):
    """Return ?next= only if it points back to this site."""
    nxt = request.GET.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return default


def _login_redirect(request, url_name):
    return redirect(f"{reverse(url_name)}?{urlencode({'next': request.get_full_path()})}")


def client_required(view):
    """Only logged-in users that have a ClientProfile. Sets request.portal_client."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _login_redirect(request, "client_login")
        profile = ClientProfile.objects.select_related("client").filter(user=request.user).first()
        if profile is None:
            messages.error(request, "Please sign in with a client account to open the client portal.")
            return redirect("client_login")
        request.client_profile = profile
        request.portal_client = profile.client
        return view(request, *args, **kwargs)
    return wrapper


def staff_required(view):
    """Only active staff users."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _login_redirect(request, "admin_login")
        if not request.user.is_staff:
            messages.error(request, "This area is for agency staff only.")
            return redirect("admin_login")
        return view(request, *args, **kwargs)
    return wrapper
