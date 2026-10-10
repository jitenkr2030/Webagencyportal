"""Staff console: manage clients' messages, documents, tickets and portal accounts."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, F, Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.views.decorators.http import require_POST

from .communication import create_message, notify_client
from .decorators import staff_required
from .forms import MessageForm, StaffDocumentForm
from .models import (ChangeRequest, Client, ClientProfile, Design, Document, Lead, Meeting,
                     Message, Project, SupportTicket)
from .services import dashboard_metrics

CLOSED_TICKET = ["Resolved", "Closed"]
TICKET_STATUSES = ["Open", "In Progress", "Resolved", "Closed"]


@staff_required
def staff_dashboard(request):
    """staff_dashboard.html"""
    context = {
        "metrics": dashboard_metrics(),
        "unread_from_clients": Message.objects.filter(from_staff=False, is_read=False).count(),
        "recent_client_messages": Message.objects.filter(from_staff=False)
            .select_related("client", "document").order_by("-created_at")[:5],
        "pending_designs": Design.objects.filter(approval_status="Under Review").select_related("project__client"),
        "pending_changes": ChangeRequest.objects.filter(status="Pending Client Approval")
            .select_related("project", "client"),
        "meeting_requests": Meeting.objects.filter(status="Requested").select_related("client", "project"),
        "open_tickets": SupportTicket.objects.exclude(status__in=CLOSED_TICKET).select_related("client")[:6],
        "recent_documents": Document.objects.select_related("client")[:6],
        "new_leads": Lead.objects.exclude(status__in=["Won", "Lost"])[:5],
        "projects": Project.objects.select_related("client").exclude(status="Completed"),
    }
    return render(request, "portal/staff_dashboard.html", context)


@staff_required
def staff_inbox(request):
    """staff_inbox.html - all client conversations, with the selected thread on the right."""
    conversations = (
        Client.objects
        .annotate(last_at=Max("messages__created_at"),
                  unread=Count("messages", filter=Q(messages__from_staff=False, messages__is_read=False)))
        .order_by(F("last_at").desc(nulls_last=True), "company")
    )
    selected = None
    form = None
    thread = []
    selected_id = request.GET.get("client", "")
    if selected_id.isdigit():
        selected = get_object_or_404(Client, pk=int(selected_id))

    if selected is not None:
        # opening or replying to a conversation marks the client's messages as read
        Message.objects.filter(client=selected, from_staff=False, is_read=False).update(is_read=True)
        if request.method == "POST":
            form = MessageForm(request.POST, request.FILES, client=selected)
            if form.is_valid():
                d = form.cleaned_data
                create_message(client=selected, user=request.user, from_staff=True,
                               body=d["body"].strip(), project=d["project"], upload=d["attachment"])
                notify_client(selected, "New message from the PixelForge team", reverse("client_messages"))
                messages.success(request, f"Message sent to {selected.company}.")
                return redirect(f"{reverse('staff_inbox')}?client={selected.pk}")
        else:
            form = MessageForm(client=selected)
        thread = list(selected.messages.select_related("sender", "client", "document", "project"))

    return render(request, "portal/staff_inbox.html", {
        "conversations": conversations, "selected": selected, "thread": thread,
        "form": form, "viewer_is_staff": True,
    })


@staff_required
def staff_documents(request):
    """staff_documents.html - every shared file, upload for any client."""
    if request.method == "POST":
        form = StaffDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            d = form.cleaned_data
            doc = Document.objects.create(
                client=d["client"], project=d["project"], title=d["title"], category=d["category"],
                description=d["description"], file=d["file"], uploaded_by=request.user,
                from_staff=True, visible_to_client=d["visible_to_client"])
            if doc.visible_to_client:
                notify_client(doc.client, f"New document shared: {doc.title}", reverse("client_documents"))
            messages.success(request, f"'{doc.title}' uploaded for {doc.client.company}.")
            return redirect(f"{reverse('staff_documents')}?client={doc.client_id}")
    else:
        initial = {}
        if request.GET.get("client", "").isdigit():
            initial["client"] = int(request.GET["client"])
        form = StaffDocumentForm(initial=initial)

    docs = Document.objects.select_related("client", "project", "uploaded_by")
    q = request.GET.get("q", "").strip()
    client_id = request.GET.get("client", "")
    category = request.GET.get("category", "")
    if q:
        docs = docs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(client__company__icontains=q))
    if client_id.isdigit():
        docs = docs.filter(client_id=int(client_id))
    if category:
        docs = docs.filter(category=category)

    return render(request, "portal/staff_documents.html", {
        "documents": docs, "form": form, "q": q, "client_filter": client_id, "category": category,
        "clients": Client.objects.all(), "categories": Document.CATEGORIES,
    })


@staff_required
def staff_tickets(request):
    """staff_tickets.html - update status / assignee of support tickets."""
    if request.method == "POST":
        ticket = get_object_or_404(SupportTicket, pk=request.POST.get("ticket_id"))
        status = request.POST.get("status", "")
        if status in TICKET_STATUSES:
            ticket.status = status
            ticket.assigned_to = request.POST.get("assigned_to", "").strip()[:100] or ticket.assigned_to
            ticket.save()
            notify_client(ticket.client, f"Ticket #{ticket.pk} '{ticket.subject}' is now {ticket.status}",
                          reverse("client_support"))
            messages.success(request, f"Ticket #{ticket.pk} updated.")
        else:
            messages.error(request, "Invalid status.")
        return redirect(request.get_full_path())

    status = request.GET.get("status", "")
    tickets = SupportTicket.objects.select_related("client", "project")
    if status == "open":
        tickets = tickets.exclude(status__in=CLOSED_TICKET)
    elif status in TICKET_STATUSES:
        tickets = tickets.filter(status=status)
    return render(request, "portal/staff_tickets.html", {
        "tickets": tickets, "statuses": TICKET_STATUSES, "status_filter": status})


@staff_required
@require_POST
def meeting_confirm(request, pk):
    """Confirm (or decline) a meeting a client requested."""
    meeting = get_object_or_404(Meeting, pk=pk, status="Requested")
    if request.POST.get("decision") == "decline":
        meeting.status = "Declined"
        text = f"Your meeting request '{meeting.meeting}' could not be accommodated. Please propose another time."
    else:
        meeting.status = "Scheduled"
        text = f"Meeting confirmed: {meeting.meeting} on {meeting.date:%d %b %Y} at {meeting.time:%H:%M}"
    meeting.save()
    notify_client(meeting.client, text, reverse("client_meetings"))
    messages.success(request, f"Meeting '{meeting.meeting}': {meeting.status}.")
    return redirect("staff_dashboard")


@staff_required
def staff_accounts(request):
    """staff_accounts.html - create / reset / disable client portal logins."""
    User = get_user_model()
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            client = get_object_or_404(Client, pk=request.POST.get("client_id"))
            username = (request.POST.get("username", "").strip() or f"client{client.pk}")[:150]
            email = request.POST.get("email", "").strip() or client.email
            if User.objects.filter(username__iexact=username).exists():
                messages.error(request, f"Username '{username}' already exists. Choose another.")
            else:
                password = get_random_string(10)
                first, _, last = client.contact_name.partition(" ")
                user = User.objects.create_user(username=username, email=email, password=password,
                                                first_name=first, last_name=last)
                ClientProfile.objects.create(user=user, client=client)
                messages.success(request, f"Login created for {client.company}. Username: {username} - "
                                          f"temporary password: {password} (shown only once, share it securely).")
        elif action in ("reset", "toggle"):
            profile = get_object_or_404(ClientProfile.objects.select_related("user"), pk=request.POST.get("profile_id"))
            if action == "reset":
                password = get_random_string(10)
                profile.user.set_password(password)
                profile.user.save()
                messages.success(request, f"New password for {profile.user.username}: {password} "
                                          "(shown only once, share it securely).")
            else:
                profile.user.is_active = not profile.user.is_active
                profile.user.save()
                state = "enabled" if profile.user.is_active else "disabled"
                messages.success(request, f"Login {profile.user.username} {state}.")
        return redirect("staff_accounts")

    clients = Client.objects.prefetch_related("profiles__user")
    return render(request, "portal/staff_accounts.html", {"clients": clients})
