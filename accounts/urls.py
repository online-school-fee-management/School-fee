from django.urls import path

from . import password_views, views

app_name = "accounts"

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("password/", password_views.change_password, name="change_password"),
]
