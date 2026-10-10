"""Business logic: dashboard metrics and per-client summaries."""
from decimal import Decimal

from django.db.models import Count, Sum

from .models import (AMCPlan, Bug, Client, Invoice, Lead, Payment, Project,
                     SupportTicket, Task)

ZERO = Decimal("0")


def dashboard_metrics():
    """Same metrics as the 'Dashboard' sheet of the Excel file, computed live."""
    invoice_value = Invoice.objects.aggregate(t=Sum("amount"))["t"] or ZERO
    collected = Invoice.objects.aggregate(t=Sum("amount_paid"))["t"] or ZERO
    return {
        "total_clients": Client.objects.count(),
        "total_leads": Lead.objects.count(),
        "active_projects": Project.objects.filter(status="In Progress").count(),
        "completed_tasks": Task.objects.filter(status="Completed").count(),
        "open_bugs": Bug.objects.filter(status="Open").count(),
        "open_tickets": SupportTicket.objects.exclude(status__in=["Resolved", "Closed"]).count(),
        "invoice_value": invoice_value,
        "collected": collected,
        "outstanding": invoice_value - collected,
        "active_amc": AMCPlan.objects.filter(status="Active").count(),
    }


def client_summary(client):
    """Billing / delivery figures for one client."""
    inv = client.invoices.aggregate(billed=Sum("amount"), paid=Sum("amount_paid"))
    billed = inv["billed"] or ZERO
    paid = inv["paid"] or ZERO
    return {
        "billed": billed,
        "paid": paid,
        "outstanding": billed - paid,
        "open_tickets": client.tickets.exclude(status__in=["Resolved", "Closed"]).count(),
        "project_count": client.projects.count(),
    }


def lead_pipeline():
    """Lead count and estimated value grouped by stage."""
    return (
        Lead.objects.values("status")
        .annotate(count=Count("id"), value=Sum("estimated_value"))
        .order_by("status")
    )
