from django.contrib import admin

from .models import AcademicYear, SchoolClass, Student


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "is_current")
    list_filter = ("school", "is_current")


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ("name", "section", "order", "school")
    list_filter = ("school",)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("student_id", "name", "school_class", "academic_year", "school", "is_active")
    list_filter = ("school", "school_class", "academic_year", "is_active")
    search_fields = ("student_id", "name", "father_name", "phone")
