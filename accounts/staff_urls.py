from django.urls import path

from . import staff_views

app_name = "staff"

urlpatterns = [
    path("", staff_views.staff_list, name="list"),
    path("add/", staff_views.staff_add, name="add"),
    path("<int:pk>/edit/", staff_views.staff_edit, name="edit"),
    path("<int:pk>/reset-password/", staff_views.staff_reset_password, name="reset_password"),
]
