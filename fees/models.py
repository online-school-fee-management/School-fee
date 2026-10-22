from decimal import Decimal

from django.db import models

from academics.models import AcademicYear, SchoolClass, Student
from tenants.models import SchoolOwnedModel


class FeeStructure(SchoolOwnedModel):
    """
    One fee for one class in one academic year.
    e.g. Class 6 / 2026 / Annual / "Annual Fee" / 5000
         Class 6 / 2026 / Exam   / "1st Term Exam" / 500
    """

    TYPE_ANNUAL = "annual"
    TYPE_EXAM = "exam"
    TYPE_CHOICES = [(TYPE_ANNUAL, "Annual"), (TYPE_EXAM, "Exam")]

    fee_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    title = models.CharField(max_length=100)
    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.PROTECT, related_name="fee_structures"
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.PROTECT, related_name="fee_structures"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["school_class__order", "school_class__name", "fee_type", "due_date", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "academic_year", "school_class", "title"],
                name="uniq_fee_title_per_class_year",
            ),
        ]

    def __str__(self):
        return f"{self.title} - {self.school_class} ({self.academic_year})"


class StudentFee(SchoolOwnedModel):
    """
    A fee that one student has to pay (a "due").
    amount is copied from the structure when generated, so later price changes
    do not silently change old dues.
    """

    STATUS_UNPAID = "unpaid"
    STATUS_PARTIAL = "partial"
    STATUS_PAID = "paid"

    # Student delete cascades to dues; once payments exist (next step) they will
    # PROTECT the due, so a student with payments cannot be deleted by accident.
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="fees")
    structure = models.ForeignKey(
        FeeStructure, on_delete=models.CASCADE, related_name="student_fees"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    waiver = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "structure"], name="uniq_fee_per_student"
            ),
        ]

    @property
    def net_amount(self):
        return self.amount - self.waiver

    @property
    def due_amount(self):
        return max(self.net_amount - self.paid_amount, Decimal("0.00"))

    @property
    def status(self):
        if self.paid_amount <= 0:
            return self.STATUS_UNPAID if self.net_amount > 0 else self.STATUS_PAID
        if self.paid_amount >= self.net_amount:
            return self.STATUS_PAID
        return self.STATUS_PARTIAL

    def __str__(self):
        return f"{self.student} - {self.structure.title}"
