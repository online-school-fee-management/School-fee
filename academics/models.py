from django.conf import settings
from django.db import models

from tenants.models import SchoolOwnedModel


class AcademicYear(SchoolOwnedModel):
    name = models.CharField(max_length=50)  # e.g. "2026"
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "name"], name="uniq_year_per_school"
            ),
        ]

    def __str__(self):
        return self.name


class SchoolClass(SchoolOwnedModel):
    name = models.CharField(max_length=50)  # e.g. "Class 6"
    section = models.CharField(max_length=20, blank=True)  # e.g. "A"
    order = models.PositiveIntegerField(default=0)  # for sorting Class 2 before Class 10

    class Meta:
        ordering = ["order", "name", "section"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "name", "section"], name="uniq_class_per_school"
            ),
        ]

    @property
    def label(self):
        return f"{self.name} - {self.section}" if self.section else self.name

    def __str__(self):
        return self.label


class Student(SchoolOwnedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="student_profile",
    )
    student_id = models.CharField(max_length=50)  # also the login username
    name = models.CharField(max_length=150)
    father_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    roll = models.PositiveIntegerField(null=True, blank=True)
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.PROTECT, related_name="students"
    )
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.PROTECT, related_name="students"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["school_class__order", "school_class__name", "roll", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "student_id"], name="uniq_student_id_per_school"
            ),
        ]

    def __str__(self):
        return f"{self.student_id} - {self.name}"
