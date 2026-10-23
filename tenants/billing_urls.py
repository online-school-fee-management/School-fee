from django.urls import path

from . import billing_views

app_name = "billing"

urlpatterns = [
    path("", billing_views.plans_page, name="plans"),
    path("checkout/", billing_views.checkout, name="checkout"),
    path("history/", billing_views.history, name="history"),
    path("invoice/<int:pk>/", billing_views.invoice, name="invoice"),
]
