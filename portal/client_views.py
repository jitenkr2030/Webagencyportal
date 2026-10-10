"""Client portal: every query is scoped to request.portal_client (the logged-in client)."""
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from .communication import create_message, notify_staff
from .decorators import client_required, safe_next
from .forms import DocumentForm, LoginForm, MeetingRequestForm, MessageForm, TicketForm
from .models import (ChangeRequest, ClientProfile, Design, Document, Meeting, Message,
                     Notification, Project, SupportTicket)
from .services import client_summary

CLOSED_TICKET = ["Resolved", "Closed"]


# ------------------------------------------------------------------ login
@require_http_methods(["GET", "POST"])
def client_login(request):
    """client_login.html"""
    if request.user.is_authenticated and ClientProfile.objects.filter(user=request.user).exists():
        return redirect("client_dashboard")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(request, username=form.cleaned_data["username"],
                            password=form.cleaned_data["password"])
        if user is None:
            messages.error(request, "Invalid username or password.")
        elif not ClientProfile.objects.filter(user=user).exists():
            messages.error(request, "This account is not a client account. Staff: use the Staff Login.")
        else:
            login(request, user)
            return redirect(safe_next(request, reverse("client_dashboard")))
    return render(request, "portal/client_login.html", {"form": form})


# -------------------------------------------------------------- dashboard
@client_required
def client_dashboard(request):
    """client_dashboard.html - the client's own overview."""
    client = request.portal_client
    projects = list(client.projects.all())
    avg = round(sum(p.completion for p in projects) / len(projects)) if projects else 0
    context = {
        "client": client,
        "summary": client_summary(client),
        "projects": projects,
        "avg_completion": avg,
        "pending_designs": Design.objects.filter(
            project__client=client, approval_status="Under Review").select_related("project"),
        "pending_changes": client.change_requests.filter(
            status="Pending Client Approval").select_related("project"),
        "due_invoices": client.invoices.exclude(status="Paid").select_related("project"),
        "open_tickets": client.tickets.exclude(status__in=CLOSED_TICKET).select_related("project")[:4],
        "meetings": client.meetings.select_related("project").order_by("-date", "-time")[:4],
        "recent_messages": client.messages.select_related("sender", "document").order_by("-created_at")[:4],
        "recent_documents": client.documents.filter(visible_to_client=True).select_related("project")[:4],
        "notifications": Notification.objects.filter(user=request.user)[:5],
        "today": timezone.localdate(),
    }
    return render(request, "portal/client_dashboard.html", context)


# --------------------------------------------------------------- projects
@client_required
def client_projects(request):
    """client_projects.html"""
    projects = request.portal_client.projects.all()
    return render(request, "portal/client_projects.html", {"client": request.portal_client, "projects": projects})


@client_required
def client_project_detail(request, pk):
    """client_project_detail.html - tasks, designs, bugs, changes, files for ONE project."""
    client = request.portal_client
    project = get_object_or_404(Project.objects.select_related("proposal"), pk=pk, client=client)
    context = {
        "client": client,
        "project": project,
        "tasks": project.tasks.all(),
        "designs": project.designs.all(),
        "bugs": project.bugs.all(),
        "websites": project.websites.all(),
        "change_requests": project.change_requests.all(),
        "documents": project.documents.filter(visible_to_client=True),
        "meetings": project.meetings.all(),
    }
    return render(request, "portal/client_project_detail.html", context)


@client_required
@require_POST
def design_respond(request, pk):
    """Client approves a design or asks for changes."""
    design = get_object_or_404(Design.objects.select_related("project"), pk=pk, project__client=request.portal_client)
    decision = request.POST.get("decision")
    if design.approval_status != "Under Review":
        messages.error(request, "This design is not waiting for your approval.")
    elif decision not in ("approve", "changes"):
        messages.error(request, "Invalid choice.")
    else:
        design.approval_status = "Client Approved" if decision == "approve" else "Changes Requested"
        design.client_feedback = request.POST.get("feedback", "").strip()[:1000]
        design.save()
        verb = "approved" if decision == "approve" else "requested changes on"
        notify_staff(f"{request.portal_client.company} {verb} design '{design.design} {design.version}'",
                     reverse("staff_dashboard"))
        messages.success(request, f"Design {design.design} {design.version}: {design.approval_status}.")
    return redirect("client_project_detail", pk=design.project_id)


@client_required
@require_POST
def change_request_respond(request, pk):
    """Client approves or rejects a change request (extra cost / days)."""
    cr = get_object_or_404(ChangeRequest, pk=pk, client=request.portal_client)
    decision = request.POST.get("decision")
    if cr.status != "Pending Client Approval":
        messages.error(request, "This change request has already been answered.")
    elif decision not in ("approve", "reject"):
        messages.error(request, "Invalid choice.")
    else:
        cr.status = "Approved" if decision == "approve" else "Rejected"
        cr.client_feedback = request.POST.get("feedback", "").strip()[:1000]
        cr.save()
        notify_staff(f"{request.portal_client.company} {cr.status.lower()} change request '{cr.request}'",
                     reverse("staff_dashboard"))
        messages.success(request, f"Change request {cr.status.lower()}.")
    return redirect("client_project_detail", pk=cr.project_id)


# ---------------------------------------------------------------- invoices
@client_required
def client_invoices(request):
    """client_invoices.html"""
    client = request.portal_client
    return render(request, "portal/client_invoices.html", {
        "client": client,
        "summary": client_summary(client),
        "invoices": client.invoices.select_related("project"),
        "payments": client.payments.select_related("invoice", "project").order_by("-id"),
        "invoice_docs": client.documents.filter(visible_to_client=True, category="Invoice"),
    })


# ---------------------------------------------------------------- messages
@client_required
def client_messages(request):
    """client_messages.html - chat with the agency team."""
    client = request.portal_client
    project_filter = request.GET.get("project", "")

    if request.method == "POST":
        form = MessageForm(request.POST, request.FILES, client=client)
        if form.is_valid():
            d = form.cleaned_data
            create_message(client=client, user=request.user, from_staff=False,
                           body=d["body"].strip(), project=d["project"], upload=d["attachment"])
            notify_staff(f"New message from {client.company}", f"{reverse('staff_inbox')}?client={client.pk}")
            messages.success(request, "Message sent.")
            return redirect(request.get_full_path())
    else:
        form = MessageForm(client=client, initial={"project": project_filter or None})

    thread = client.messages.select_related("sender", "client", "document", "project")
    unread = Message.objects.filter(client=client, from_staff=True, is_read=False)
    if project_filter.isdigit():
        thread = thread.filter(project_id=int(project_filter))
        unread = unread.filter(project_id=int(project_filter))
    thread = list(thread)
    unread.update(is_read=True)

    return render(request, "portal/client_messages.html", {
        "client": client, "thread": thread, "form": form,
        "projects": client.projects.all(), "project_filter": project_filter,
        "viewer_is_staff": False,
    })


# --------------------------------------------------------------- documents
@client_required
def client_documents(request):
    """client_documents.html - browse, download and upload files."""
    client = request.portal_client
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES, client=client)
        if form.is_valid():
            d = form.cleaned_data
            doc = Document.objects.create(
                client=client, project=d["project"], title=d["title"], category=d["category"],
                description=d["description"], file=d["file"], uploaded_by=request.user,
                from_staff=False, visible_to_client=True)
            notify_staff(f"{client.company} uploaded '{doc.title}'", f"{reverse('staff_documents')}?client={client.pk}")
            messages.success(request, f"'{doc.title}' uploaded and shared with the agency.")
            return redirect("client_documents")
    else:
        form = DocumentForm(client=client)

    docs = client.documents.filter(visible_to_client=True).select_related("project", "uploaded_by")
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    project = request.GET.get("project", "")
    if q:
        docs = docs.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if category:
        docs = docs.filter(category=category)
    if project.isdigit():
        docs = docs.filter(project_id=int(project))

    return render(request, "portal/client_documents.html", {
        "client": client, "documents": docs, "form": form, "q": q, "category": category,
        "project_filter": project, "categories": Document.CATEGORIES, "projects": client.projects.all(),
    })


@login_required(login_url="client_login")
def document_download(request, pk):
    """Permission-checked download used by clients AND staff. Files are never served directly."""
    doc = get_object_or_404(Document, pk=pk)
    user = request.user
    allowed = user.is_staff or (
        doc.visible_to_client
        and ClientProfile.objects.filter(user=user, client_id=doc.client_id).exists()
    )
    if not allowed:
        raise Http404("Document not found.")
    try:
        handle = doc.file.open("rb")
    except (FileNotFoundError, ValueError):
        raise Http404("File is missing on the server.")
    return FileResponse(handle, as_attachment=True, filename=doc.filename)


@login_required(login_url="client_login")
@require_POST
def document_delete(request, pk):
    """Staff may delete any file; a client only the files they uploaded themselves."""
    doc = get_object_or_404(Document, pk=pk)
    user = request.user
    if not (user.is_staff or (doc.client_id and not doc.from_staff and doc.uploaded_by_id == user.id
                              and ClientProfile.objects.filter(user=user, client_id=doc.client_id).exists())):
        raise Http404("Document not found.")
    title = doc.title
    doc.delete()
    messages.success(request, f"'{title}' deleted.")
    nxt = request.POST.get("next", "")
    if not (nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()})):
        nxt = reverse("staff_documents" if user.is_staff else "client_documents")
    return redirect(nxt)


# ----------------------------------------------------------------- support
@client_required
def client_support(request):
    """client_support.html - raise and track support tickets."""
    client = request.portal_client
    if request.method == "POST":
        form = TicketForm(request.POST, client=client)
        if form.is_valid():
            d = form.cleaned_data
            ticket = SupportTicket.objects.create(
                client=client, project=d["project"], subject=d["subject"], priority=d["priority"],
                description=d["description"], assigned_to="Unassigned", status="Open")
            notify_staff(f"New {ticket.priority} ticket from {client.company}: {ticket.subject}",
                         reverse("staff_tickets"))
            messages.success(request, f"Ticket #{ticket.pk} created. We will get back to you soon.")
            return redirect("client_support")
    else:
        form = TicketForm(client=client)
    return render(request, "portal/client_support.html", {
        "client": client, "form": form,
        "tickets": client.tickets.select_related("project"),
    })


# ---------------------------------------------------------------- meetings
@client_required
def client_meetings(request):
    """client_meetings.html - meetings and meeting requests."""
    client = request.portal_client
    if request.method == "POST":
        form = MeetingRequestForm(request.POST, client=client)
        if form.is_valid():
            d = form.cleaned_data
            meeting = Meeting.objects.create(
                client=client, project=d["project"], meeting=d["meeting"], date=d["date"],
                time=d["time"], platform=d["platform"], status="Requested")
            notify_staff(f"{client.company} requested a meeting: {meeting.meeting} on {meeting.date}",
                         reverse("staff_dashboard"))
            messages.success(request, "Meeting requested. You will be notified once it is confirmed.")
            return redirect("client_meetings")
    else:
        form = MeetingRequestForm(client=client)
    return render(request, "portal/client_meetings.html", {
        "client": client, "form": form, "today": timezone.localdate(),
        "meetings": client.meetings.select_related("project").order_by("-date", "-time"),
    })


# ----------------------------------------------------------- notifications
@login_required(login_url="client_login")
def notifications(request):
    """notifications.html - for both clients and staff."""
    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return redirect("notifications")
    return render(request, "portal/notifications.html", {
        "items": Notification.objects.filter(user=request.user)[:100]})


@login_required(login_url="client_login")
def notification_open(request, pk):
    """Mark one notification as read and jump to its link."""
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    n.is_read = True
    n.save(update_fields=["is_read"])
    if n.link and url_has_allowed_host_and_scheme(n.link, allowed_hosts={request.get_host()}):
        return redirect(n.link)
    return redirect("notifications")
