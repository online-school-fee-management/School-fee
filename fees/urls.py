from django.urls import path

from . import views

app_name = "fees"

urlpatterns = [
    path("fees/", views.fee_list, name="fee_list"),
    path("fees/add/", views.fee_add, name="fee_add"),
    path("fees/generate-all/", views.fee_generate_all, name="fee_generate_all"),
    path("fees/<int:pk>/edit/", views.fee_edit, name="fee_edit"),
    path("fees/<int:pk>/delete/", views.fee_delete, name="fee_delete"),
    path("fees/<int:pk>/generate/", views.fee_generate, name="fee_generate"),
]
