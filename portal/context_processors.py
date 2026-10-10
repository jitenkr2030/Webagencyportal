from .models import ClientProfile, Message, Notification


def portal_context(request):
    """Values used by the navigation bar / sidebars on every page."""
    ctx = {"is_client_user": False, "is_staff_user": False,
           "unread_notifications": 0, "unread_messages": 0, "nav_client": None}
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return ctx
    ctx["unread_notifications"] = Notification.objects.filter(user=user, is_read=False).count()
    profile = ClientProfile.objects.select_related("client").filter(user=user).first()
    if profile:
        ctx["is_client_user"] = True
        ctx["nav_client"] = profile.client
        ctx["unread_messages"] = Message.objects.filter(
            client=profile.client, from_staff=True, is_read=False).count()
    elif user.is_staff:
        ctx["is_staff_user"] = True
        ctx["unread_messages"] = Message.objects.filter(from_staff=False, is_read=False).count()
    return ctx
