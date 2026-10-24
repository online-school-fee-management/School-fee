from django.urls import path

from . import website_views

app_name = "website"

urlpatterns = [
    path("", website_views.website_dashboard, name="dashboard"),
    path("settings/", website_views.website_settings, name="settings"),
    path("notices/", website_views.notice_list, name="notices"),
    path("notices/add/", website_views.notice_add, name="notice_add"),
    path("notices/<int:pk>/edit/", website_views.notice_edit, name="notice_edit"),
    path("notices/<int:pk>/delete/", website_views.notice_delete, name="notice_delete"),
    path("gallery/", website_views.gallery_list, name="gallery"),
    path("gallery/add/", website_views.gallery_add, name="gallery_add"),
    path("gallery/<int:pk>/edit/", website_views.gallery_edit, name="gallery_edit"),
    path("gallery/<int:pk>/delete/", website_views.gallery_delete, name="gallery_delete"),
    path("teachers/", website_views.teacher_list, name="teachers"),
    path("teachers/add/", website_views.teacher_add, name="teacher_add"),
    path("teachers/<int:pk>/edit/", website_views.teacher_edit, name="teacher_edit"),
    path("teachers/<int:pk>/delete/", website_views.teacher_delete, name="teacher_delete"),
]
