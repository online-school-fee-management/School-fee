from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.home, name="home"),
    path("fees/", views.dues, name="dues"),
    path("fees/<int:pk>/pay/", views.pay, name="pay"),
    path("history/", views.history, name="history"),
]
