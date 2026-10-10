from django.urls import path

from . import client_views as cv
from . import staff_views as sv
from . import views

urlpatterns = [
    # ---- public website
    path("", views.index, name="index"),                                  # index.html (home)

    # ---- authentication
    path("admin-login/", views.admin_login, name="admin_login"),          # admin_login.html (staff)
    path("portal/login/", cv.client_login, name="client_login"),          # client_login.html
    path("logout/", views.logout_view, name="logout"),                    # POST only

    # ---- client portal (each client sees only their own data)
    path("portal/", cv.client_dashboard, name="client_dashboard"),
    path("portal/projects/", cv.client_projects, name="client_projects"),
    path("portal/projects/<int:pk>/", cv.client_project_detail, name="client_project_detail"),
    path("portal/designs/<int:pk>/respond/", cv.design_respond, name="design_respond"),
    path("portal/change-requests/<int:pk>/respond/", cv.change_request_respond, name="change_request_respond"),
    path("portal/invoices/", cv.client_invoices, name="client_invoices"),
    path("portal/messages/", cv.client_messages, name="client_messages"),
    path("portal/documents/", cv.client_documents, name="client_documents"),
    path("portal/support/", cv.client_support, name="client_support"),
    path("portal/meetings/", cv.client_meetings, name="client_meetings"),

    # ---- shared (clients + staff)
    path("documents/<int:pk>/download/", cv.document_download, name="document_download"),
    path("documents/<int:pk>/delete/", cv.document_delete, name="document_delete"),
    path("notifications/", cv.notifications, name="notifications"),
    path("notifications/<int:pk>/open/", cv.notification_open, name="notification_open"),

    # ---- staff console
    path("staff/", sv.staff_dashboard, name="staff_dashboard"),
    path("staff/inbox/", sv.staff_inbox, name="staff_inbox"),
    path("staff/documents/", sv.staff_documents, name="staff_documents"),
    path("staff/tickets/", sv.staff_tickets, name="staff_tickets"),
    path("staff/meetings/<int:pk>/confirm/", sv.meeting_confirm, name="meeting_confirm"),
    path("staff/accounts/", sv.staff_accounts, name="staff_accounts"),
    path("staff/clients/", views.clients, name="clients"),               # clients.html (staff only)

    # ---- JSON API
    path("api/dashboard/", views.api_dashboard, name="api_dashboard"),
    path("api/services/", views.api_services, name="api_services"),
    path("api/clients/", views.api_clients, name="api_clients"),
]
