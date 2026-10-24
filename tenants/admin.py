from django.contrib import admin

from .models import (
    GalleryImage,
    Notice,
    School,
    SchoolWebsite,
    SubscriptionPayment,
    TeacherProfile,
)


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


@admin.register(SchoolWebsite)
class SchoolWebsiteAdmin(admin.ModelAdmin):
    list_display = ("school", "hero_title", "admissions_open", "updated_at")
    search_fields = ("school__name", "school__subdomain", "hero_title")


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "school", "published_on", "is_important", "is_active")
    list_filter = ("school", "is_important", "is_active")
    search_fields = ("title", "content", "school__name")


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ("title", "school", "display_order", "is_active", "created_at")
    list_filter = ("school", "is_active")
    search_fields = ("title", "caption", "school__name")


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "designation", "display_order", "is_active")
    list_filter = ("school", "is_active")
    search_fields = ("name", "designation", "qualification", "school__name")
