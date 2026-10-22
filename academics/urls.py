from django.urls import path

from . import views

app_name = "academics"

urlpatterns = [
    # Academic years
    path("years/", views.year_list, name="year_list"),
    path("years/<int:pk>/edit/", views.year_edit, name="year_edit"),
    path("years/<int:pk>/delete/", views.year_delete, name="year_delete"),
    path("years/<int:pk>/current/", views.year_current, name="year_current"),
    # Classes
    path("classes/", views.class_list, name="class_list"),
    path("classes/<int:pk>/edit/", views.class_edit, name="class_edit"),
    path("classes/<int:pk>/delete/", views.class_delete, name="class_delete"),
    # Students
    path("students/", views.student_list, name="student_list"),
    path("students/add/", views.student_add, name="student_add"),
    path("students/import/", views.student_import, name="student_import"),
    path("students/import/sample/", views.student_import_sample, name="student_import_sample"),
    path("students/<int:pk>/edit/", views.student_edit, name="student_edit"),
    path("students/<int:pk>/delete/", views.student_delete, name="student_delete"),
    path("students/<int:pk>/reset-password/", views.student_reset_password, name="student_reset_password"),
]
