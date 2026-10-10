"""Views: index (home), clients, admin login, plus small JSON APIs."""
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from .decorators import safe_next, staff_required
from .forms import EnquiryForm, LoginForm
from .models import Client, ClientProfile, Project, Service
from .services import client_summary, dashboard_metrics


def index(request):
    """index.html - public landing page (the first page Django shows)."""
    if request.method == "POST":
        form = EnquiryForm(request.POST)
        if form.is_valid():
            lead = form.save()
            messages.success(
                request,
                f"Thank you {lead.contact_name}! Your enquiry (Lead #{lead.pk}) has been received. "
                "Our sales team will contact you shortly.",
            )
            return redirect("/#enquiry")
    else:
        form = EnquiryForm()

    metrics = dashboard_metrics()
    context = {
        "services": Service.objects.filter(status="Active"),
        "projects": Project.objects.select_related("client")[:6],
        "stats": {
            "clients": metrics["total_clients"],
            "projects": Project.objects.count(),
            "live_sites": Project.objects.filter(websites__deployment_status="Live").distinct().count(),
            "active_amc": metrics["active_amc"],
        },
        "form": form,
    }
    return render(request, "portal/index.html", context)


@staff_required
def clients(request):
    """clients.html - staff-only client directory with search, filter and detail panel."""
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()

    qs = Client.objects.all()
    if q:
        qs = qs.filter(
            Q(company__icontains=q) | Q(contact_name__icontains=q)
            | Q(email__icontains=q) | Q(city__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)

    rows = [{"client": c, "summary": client_summary(c)} for c in qs]

    selected = None
    selected_id = request.GET.get("client")
    if selected_id and selected_id.isdigit():
        obj = get_object_or_404(
            Client.objects.prefetch_related(
                "projects", "invoices", "websites", "tickets", "amc_plans",
                "requirements", "proposals", "meetings", "change_requests",
            ),
            pk=int(selected_id),
        )
        selected = {"client": obj, "summary": client_summary(obj)}

    context = {
        "rows": rows,
        "selected": selected,
        "q": q,
        "status": status,
        "statuses": Client.objects.order_by("status").values_list("status", flat=True).distinct(),
        "metrics": dashboard_metrics(),
    }
    return render(request, "portal/clients.html", context)


@require_http_methods(["GET", "POST"])
def admin_login(request):
    """admin_login.html - staff sign-in; success goes to the staff console."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("staff_dashboard")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        if user is None:
            messages.error(request, "Invalid username or password.")
        elif not user.is_staff:
            messages.error(request, "This account does not have staff access. Clients: use the Client Login.")
        else:
            login(request, user)
            return redirect(safe_next(request, reverse("staff_dashboard")))
    return render(request, "portal/admin_login.html", {"form": form})


@require_POST
def logout_view(request):
    """Sign out (POST only) and return to the matching login page."""
    was_client = request.user.is_authenticated and ClientProfile.objects.filter(user=request.user).exists()
    logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("client_login" if was_client else "admin_login")


# ---------------------------------------------------------------- JSON API
def api_dashboard(request):
    """GET /api/dashboard/ - headline metrics (staff only)."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({"detail": "Authentication required."}, status=403)
    data = {k: (float(v) if hasattr(v, "quantize") else v) for k, v in dashboard_metrics().items()}
    return JsonResponse(data)


def api_services(request):
    """GET /api/services/ - public service catalogue."""
    items = list(
        Service.objects.filter(status="Active").values(
            "id", "name", "category", "starting_price", "delivery_days"
        )
    )
    for item in items:
        item["starting_price"] = float(item["starting_price"])
    return JsonResponse({"services": items})


def api_clients(request):
    """GET /api/clients/ - client list with billing summary (staff only)."""
    if not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({"detail": "Authentication required."}, status=403)
    out = []
    for c in Client.objects.all():
        s = client_summary(c)
        out.append({
            "id": c.pk, "company": c.company, "contact": c.contact_name, "email": c.email,
            "city": c.city, "status": c.status, "projects": s["project_count"],
            "billed": float(s["billed"]), "paid": float(s["paid"]), "outstanding": float(s["outstanding"]),
        })
    return JsonResponse({"clients": out})
