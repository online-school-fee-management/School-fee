from django.urls import path

from . import owner_plans, owner_views, views

app_name = "tenants"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("signup/done/", views.signup_done, name="signup_done"),
    path("signup/check/", views.check_subdomain, name="check_subdomain"),
    path("find-school/", views.find_school, name="find_school"),
    # Platform owner panel (superuser, main domain only)
    path("owner/", owner_views.owner_dashboard, name="owner"),
    path("owner/export/", owner_views.owner_export, name="owner_export"),
    path("owner/<int:pk>/toggle/", owner_views.owner_toggle, name="owner_toggle"),
    path("owner/<int:pk>/plan/", owner_plans.owner_plan, name="owner_plan"),
]
