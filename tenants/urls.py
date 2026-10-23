from django.urls import path

from . import views

app_name = "tenants"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("signup/done/", views.signup_done, name="signup_done"),
    path("signup/check/", views.check_subdomain, name="check_subdomain"),
    path("find-school/", views.find_school, name="find_school"),
]
