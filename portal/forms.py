import os
from decimal import Decimal

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Client, Document, Lead, Project, Service

ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv", "md",
    "png", "jpg", "jpeg", "gif", "webp", "zip", "json",
}


def validate_upload(upload):
    """Allow only common document/image types up to MAX_UPLOAD_MB."""
    ext = os.path.splitext(upload.name)[1].lstrip(".").lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            "File type '.%(ext)s' is not allowed. Allowed: %(allowed)s.",
            params={"ext": ext, "allowed": ", ".join(sorted(ALLOWED_EXTENSIONS))},
        )
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    if upload.size > limit:
        raise ValidationError("File is too large (max %(mb)s MB).", params={"mb": settings.MAX_UPLOAD_MB})


class EnquiryForm(forms.Form):
    """Public enquiry form on index.html - creates a Lead."""

    contact_name = forms.CharField(max_length=120, label="Your name")
    company = forms.CharField(max_length=160, label="Company")
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, required=False)
    service = forms.ModelChoiceField(queryset=Service.objects.none(), empty_label="Select a service")
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), required=False, label="Project details")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.filter(status="Active")

    def save(self):
        data = self.cleaned_data
        service = data["service"]
        return Lead.objects.create(
            company=data["company"],
            requirement=service.name,
            lead_source="Website",
            status="New",
            estimated_value=Decimal(service.starting_price),
            contact_name=data["contact_name"],
            email=data["email"],
            phone=data["phone"],
            message=data["message"],
        )


class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={"autofocus": True, "placeholder": "Username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Password"}))


# ------------------------------------------------------------ client portal
class MessageForm(forms.Form):
    body = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Type your message..."}),
                           label="Message")
    project = forms.ModelChoiceField(queryset=Project.objects.none(), required=False,
                                     empty_label="General (all projects)", label="Related project")
    attachment = forms.FileField(required=False, validators=[validate_upload], label="Attach a file")

    def __init__(self, *args, client=None, **kwargs):
        super().__init__(*args, **kwargs)
        if client is not None:
            self.fields["project"].queryset = Project.objects.filter(client=client)

    def clean(self):
        data = super().clean()
        if not (data.get("body") or "").strip() and not data.get("attachment"):
            raise ValidationError("Write a message or attach a file.")
        return data


class DocumentForm(forms.Form):
    title = forms.CharField(max_length=200)
    category = forms.ChoiceField(choices=Document.UPLOAD_CATEGORIES)
    project = forms.ModelChoiceField(queryset=Project.objects.none(), required=False,
                                     empty_label="General (no project)")
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    file = forms.FileField(validators=[validate_upload])

    def __init__(self, *args, client=None, **kwargs):
        super().__init__(*args, **kwargs)
        if client is not None:
            self.fields["project"].queryset = Project.objects.filter(client=client)


class StaffDocumentForm(DocumentForm):
    field_order = ["client", "title", "category", "project", "description", "file", "visible_to_client"]
    client = forms.ModelChoiceField(queryset=Client.objects.all())
    visible_to_client = forms.BooleanField(required=False, initial=True,
                                           label="Visible to client (untick for internal only)")

    def __init__(self, *args, **kwargs):
        kwargs.pop("client", None)
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.select_related("client")

    def clean(self):
        data = super().clean()
        client, project = data.get("client"), data.get("project")
        if client and project and project.client_id != client.pk:
            self.add_error("project", "This project does not belong to the selected client.")
        return data


class TicketForm(forms.Form):
    PRIORITIES = [("Low", "Low"), ("Medium", "Medium"), ("High", "High"), ("Critical", "Critical")]
    project = forms.ModelChoiceField(queryset=Project.objects.none())
    subject = forms.CharField(max_length=200)
    priority = forms.ChoiceField(choices=PRIORITIES, initial="Medium")
    description = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), label="Describe the problem")

    def __init__(self, *args, client=None, **kwargs):
        super().__init__(*args, **kwargs)
        if client is not None:
            self.fields["project"].queryset = Project.objects.filter(client=client)


class MeetingRequestForm(forms.Form):
    PLATFORMS = [("Google Meet", "Google Meet"), ("Zoom", "Zoom"), ("Phone Call", "Phone Call")]
    project = forms.ModelChoiceField(queryset=Project.objects.none())
    meeting = forms.CharField(max_length=200, label="Meeting topic")
    date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    platform = forms.ChoiceField(choices=PLATFORMS)

    def __init__(self, *args, client=None, **kwargs):
        super().__init__(*args, **kwargs)
        if client is not None:
            self.fields["project"].queryset = Project.objects.filter(client=client)

    def clean_date(self):
        value = self.cleaned_data["date"]
        if value < timezone.localdate():
            raise ValidationError("Please choose today or a future date.")
        return value
