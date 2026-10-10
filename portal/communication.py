"""Helpers for notifications, chat messages and document creation."""
from django.contrib.auth import get_user_model

from .models import Document, Message, Notification


def notify_user(user, title, link=""):
    if user and user.is_active:
        Notification.objects.create(user=user, title=title[:240], link=link)


def notify_staff(title, link=""):
    User = get_user_model()
    Notification.objects.bulk_create([
        Notification(user=u, title=title[:240], link=link)
        for u in User.objects.filter(is_staff=True, is_active=True)
    ])


def notify_client(client, title, link=""):
    Notification.objects.bulk_create([
        Notification(user=p.user, title=title[:240], link=link)
        for p in client.profiles.select_related("user") if p.user.is_active
    ])


def create_message(*, client, user, from_staff, body="", project=None, upload=None):
    """Create a chat message; an attached file becomes a shared Document."""
    document = None
    if upload:
        document = Document.objects.create(
            client=client, project=project, title=upload.name[:200],
            category="Message Attachment", file=upload, uploaded_by=user,
            from_staff=from_staff, visible_to_client=True,
        )
    return Message.objects.create(
        client=client, project=project, sender=user, from_staff=from_staff,
        body=body, document=document, is_read=False,
    )
