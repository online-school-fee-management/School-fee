from django.contrib import admin

from .models import School, SubscriptionPayment


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "subdomain", "eiin", "plan", "plan_expires_at", "is_active", "created_at")
    list_filter = ("is_active", "plan")
    search_fields = ("name", "subdomain", "eiin")


@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "school", "plan", "months", "amount", "method", "period_end", "created_at")
    list_filter = ("plan", "method")
    search_fields = ("school__name", "school__subdomain", "reference")
