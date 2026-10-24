from django.urls import path

from . import views

app_name = "receipts"

urlpatterns = [
    path(
        "verify/<int:pk>/<str:token>/",
        views.verify_receipt,
        name="verify",
    ),
]
