from django.urls import path

from . import views

app_name = "accounting"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("setup/", views.setup, name="setup"),
    path("entries/", views.entry_list, name="entries"),
    path("entries/new/", views.entry_create, name="entry_create"),
    path("entries/<int:pk>/", views.entry_detail, name="entry_detail"),
    path("entries/<int:pk>/edit/", views.entry_edit, name="entry_edit"),
    path("entries/<int:pk>/void/", views.entry_void, name="entry_void"),
    path("ledger/", views.ledger, name="ledger"),
    path("import/", views.import_entries, name="import"),
    path("import/template/", views.import_template, name="import_template"),
    path("export/", views.export_entries, name="export"),
]
