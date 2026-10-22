from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class SchoolUserAdmin(UserAdmin):
    list_display = ("username", "school", "role", "first_name", "is_active")
    list_filter = ("school", "role", "is_active")
    search_fields = ("username", "first_name", "last_name")
    fieldsets = UserAdmin.fieldsets + (
        ("School", {"fields": ("school", "role")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("School", {"fields": ("school", "role")}),
    )
