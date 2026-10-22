from django.contrib import admin

from .models import FeeStructure, StudentFee


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ("title", "fee_type", "school_class", "academic_year", "amount", "due_date", "is_active", "school")
    list_filter = ("school", "fee_type", "academic_year", "is_active")


@admin.register(StudentFee)
class StudentFeeAdmin(admin.ModelAdmin):
    list_display = ("student", "structure", "amount", "waiver", "paid_amount", "school")
    list_filter = ("school",)
    search_fields = ("student__student_id", "student__name")
