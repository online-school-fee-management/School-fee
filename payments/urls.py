from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("payments/", views.payment_status, name="payment_status"),
    path("payments/export/", views.payment_export, name="payment_export"),
    path("payments/student/<int:student_id>/", views.student_ledger, name="student_ledger"),
    path("payments/due/<int:pk>/collect/", views.collect, name="collect"),
    path("payments/due/<int:pk>/waiver/", views.set_waiver, name="set_waiver"),
    path("payments/<int:pk>/receipt/", views.receipt, name="receipt"),
    path("payments/<int:pk>/void/", views.void, name="void"),
]
