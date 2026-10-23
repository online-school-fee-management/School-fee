from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("dashboard/", include("academics.urls")),
    path("dashboard/", include("fees.urls")),
    path("dashboard/", include("payments.urls")),
    path("portal/", include("portal.urls")),
]
