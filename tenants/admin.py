from django.contrib import admin

from .models import School


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "subdomain", "eiin", "plan", "plan_expires_at", "is_active", "created_at")
    list_filter = ("is_active", "plan")
    search_fields = ("name", "subdomain", "eiin")
