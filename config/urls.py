from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("tenants.urls")),
    path("", include("accounts.urls")),
    path("dashboard/staff/", include("accounts.staff_urls")),
    path("dashboard/website/", include("tenants.website_urls")),
    path("dashboard/billing/", include("tenants.billing_urls")),
    path("dashboard/accounting/", include("accounting.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("dashboard/", include("academics.urls")),
    path("dashboard/", include("fees.urls")),
    path("dashboard/", include("payments.urls")),
    path("portal/", include("portal.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
