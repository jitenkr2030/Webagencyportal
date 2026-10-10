"""Root URL configuration. The site root (/) shows index.html."""
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Web Agency Portal Administration"
admin.site.site_title = "Web Agency Portal"
admin.site.index_title = "CRM, Projects, Billing & Support"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("portal.urls")),
]
