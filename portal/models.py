"""Database models for the Web Development Agency Portal.

Workflow covered:
Lead -> Enquiry -> Requirement -> Proposal -> Approval -> Payment -> Project ->
Design -> Development -> QA -> Client Review -> Changes -> Deployment ->
Handover -> Maintenance
"""
import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import get_valid_filename


class Client(models.Model):
    contact_name = models.CharField(max_length=120)
    email = models.EmailField()
    company = models.CharField(max_length=160)
    city = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=30, default="Lead")

    class Meta:
        ordering = ["company"]

    def __str__(self):
        return f"{self.company} ({self.contact_name})"


class Lead(models.Model):
    company = models.CharField(max_length=160)
    requirement = models.CharField(max_length=160)
    lead_source = models.CharField(max_length=60, default="Website")
    status = models.CharField(max_length=30, default="New")
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Extra fields filled by the public enquiry form on index.html
    contact_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.company} - {self.requirement}"


class Service(models.Model):
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=120)
    starting_price = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_days = models.PositiveIntegerField()
    status = models.CharField(max_length=30, default="Active")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Requirement(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="requirements")
    requirement = models.CharField(max_length=200)
    technology = models.CharField(max_length=200)
    approval_status = models.CharField(max_length=30, default="Draft")

    def __str__(self):
        return self.requirement


class Proposal(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="proposals")
    project_name = models.CharField(max_length=200)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=30, default="Draft")

    def __str__(self):
        return self.project_name

    def recalculate(self):
        self.total = self.subtotal + self.tax - self.discount
        return self.total


class Project(models.Model):
    proposal = models.ForeignKey(Proposal, null=True, blank=True, on_delete=models.SET_NULL, related_name="projects")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=200)
    project_manager = models.CharField(max_length=100)
    status = models.CharField(max_length=30, default="Planning")
    completion = models.PositiveIntegerField(default=0, help_text="Completion percentage (0-100)")
    value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Task(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    task = models.CharField(max_length=200)
    assigned_to = models.CharField(max_length=100)
    priority = models.CharField(max_length=20, default="Medium")
    status = models.CharField(max_length=30, default="Pending")
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    actual_hours = models.DecimalField(max_digits=6, decimal_places=1, default=0)

    def __str__(self):
        return self.task


class Design(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="designs")
    design = models.CharField(max_length=200)
    version = models.CharField(max_length=20)
    approval_status = models.CharField(max_length=30, default="Draft")
    client_feedback = models.TextField(blank=True)

    def __str__(self):
        return f"{self.design} {self.version}"


class Bug(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="bugs")
    bug = models.CharField(max_length=200)
    priority = models.CharField(max_length=20, default="Medium")
    assigned_to = models.CharField(max_length=100)
    status = models.CharField(max_length=30, default="Open")

    def __str__(self):
        return self.bug


class Website(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="websites")
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="websites")
    url = models.CharField(max_length=200)
    technology = models.CharField(max_length=120)
    deployment_status = models.CharField(max_length=30, default="Not Deployed")

    def __str__(self):
        return self.url


class ChangeRequest(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="change_requests")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="change_requests")
    request = models.CharField(max_length=200)
    additional_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    additional_days = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=40, default="Pending Client Approval")
    client_feedback = models.TextField(blank=True)

    def __str__(self):
        return self.request


class Invoice(models.Model):
    invoice_no = models.CharField(max_length=30, primary_key=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="invoices")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="invoices")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=30, default="Unpaid")

    class Meta:
        ordering = ["invoice_no"]

    def __str__(self):
        return self.invoice_no

    @property
    def outstanding(self):
        return self.amount - self.amount_paid


class Payment(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="payments")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="payments")
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=40)
    status = models.CharField(max_length=30, default="Pending")

    def __str__(self):
        return f"Payment {self.pk} - {self.invoice_id}"


class SupportTicket(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="tickets")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tickets")
    subject = models.CharField(max_length=200)
    priority = models.CharField(max_length=20, default="Medium")
    assigned_to = models.CharField(max_length=100, default="Unassigned")
    status = models.CharField(max_length=30, default="Open")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.subject


class AMCPlan(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="amc_plans")
    plan_name = models.CharField(max_length=120)
    billing_cycle = models.CharField(max_length=20)
    fee = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=30, default="Pending")

    class Meta:
        verbose_name = "AMC plan"

    def __str__(self):
        return f"{self.plan_name} ({self.client.company})"


class Employee(models.Model):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120)
    department = models.CharField(max_length=80)
    status = models.CharField(max_length=30, default="Active")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Timesheet(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="timesheets")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="timesheets")
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="timesheets")
    hours = models.DecimalField(max_digits=5, decimal_places=1)
    billable = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.employee.name} - {self.hours}h"


class Meeting(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="meetings")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="meetings")
    meeting = models.CharField(max_length=200)
    date = models.DateField()
    time = models.TimeField()
    platform = models.CharField(max_length=40)
    status = models.CharField(max_length=30, default="Scheduled")

    class Meta:
        ordering = ["date", "time"]

    def __str__(self):
        return self.meeting


# ====================================================================
# Client portal, communication and document sharing
# ====================================================================
class ClientProfile(models.Model):
    """Links a login (User) to a Client company so the person can use the client portal."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="client_profile")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="profiles")
    phone = models.CharField(max_length=30, blank=True)
    job_title = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return f"{self.user.username} -> {self.client.company}"


def document_upload_path(instance, filename):
    clean = get_valid_filename(os.path.basename(filename))
    return f"documents/client_{instance.client_id}/{uuid.uuid4().hex[:8]}_{clean}"


class Document(models.Model):
    CATEGORIES = [
        ("Contract", "Contract / Agreement"),
        ("Proposal", "Proposal / Quotation"),
        ("Invoice", "Invoice / Receipt"),
        ("Design", "Design / Mock-up"),
        ("Credentials", "Credentials / Access"),
        ("Report", "Report"),
        ("Content", "Content / Brand Assets"),
        ("Message Attachment", "Message Attachment"),
        ("Other", "Other"),
    ]
    UPLOAD_CATEGORIES = [c for c in CATEGORIES if c[0] != "Message Attachment"]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="documents")
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="documents")
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=CATEGORIES, default="Other")
    description = models.TextField(blank=True)
    file = models.FileField(upload_to=document_upload_path, max_length=300)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="uploaded_documents")
    from_staff = models.BooleanField(default=True, help_text="Uploaded by the agency (True) or by the client (False)")
    visible_to_client = models.BooleanField(default=True, help_text="Untick for internal-only documents")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.title

    @property
    def filename(self):
        name = os.path.basename(self.file.name or "")
        # strip the random prefix added by document_upload_path
        return name.split("_", 1)[1] if "_" in name and len(name.split("_", 1)[0]) == 8 else name

    @property
    def extension(self):
        return os.path.splitext(self.filename)[1].lstrip(".").upper() or "FILE"

    @property
    def size_display(self):
        try:
            size = self.file.size
        except (OSError, ValueError):
            return "-"
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024

    def delete(self, *args, **kwargs):
        storage, name = self.file.storage, self.file.name
        result = super().delete(*args, **kwargs)
        if name:
            try:
                storage.delete(name)
            except OSError:
                pass
        return result


class Message(models.Model):
    """One chat message between a client and the agency team."""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="messages")
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="sent_messages")
    from_staff = models.BooleanField(default=False)
    body = models.TextField(blank=True)
    document = models.ForeignKey(Document, null=True, blank=True, on_delete=models.SET_NULL, related_name="messages")
    is_read = models.BooleanField(default=False, help_text="Read by the receiving side")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.client.company}: {self.body[:40]}"

    @property
    def author_name(self):
        if self.sender and self.sender.get_full_name():
            return self.sender.get_full_name()
        return "PixelForge Team" if self.from_staff else self.client.contact_name


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=240)
    link = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.title
