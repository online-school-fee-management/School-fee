from django.conf import settings
from django.db import models
from django.utils import timezone

from fees.models import StudentFee
from tenants.models import School, SchoolOwnedModel


class Payment(SchoolOwnedModel):
    METHOD_CASH = "cash"
    METHOD_BKASH = "bkash"
    METHOD_NAGAD = "nagad"
    METHOD_BANK = "bank"
    METHOD_OTHER = "other"
    METHOD_CHOICES = [
        (METHOD_CASH, "Cash"),
        (METHOD_BKASH, "bKash"),
        (METHOD_NAGAD, "Nagad"),
        (METHOD_BANK, "Bank"),
        (METHOD_OTHER, "Other"),
    ]

    # PROTECT: a due that has payments can never be deleted by accident
    # (this also stops deleting a student / fee that has payment records).
    student_fee = models.ForeignKey(
        StudentFee, on_delete=models.PROTECT, related_name="payments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default=METHOD_CASH)
    reference = models.CharField(max_length=100, blank=True)  # bKash trx ID, bank slip no...
    note = models.CharField(max_length=200, blank=True)
    receipt_no = models.CharField(max_length=20)
    paid_at = models.DateTimeField(default=timezone.now)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="received_payments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-paid_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "receipt_no"], name="uniq_receipt_no_per_school"
            ),
        ]

    def __str__(self):
        return f"{self.receipt_no} - {self.amount}"


class ReceiptSequence(models.Model):
    """Running receipt number, one counter per school."""

    school = models.OneToOneField(
        School, on_delete=models.CASCADE, related_name="receipt_sequence"
    )
    last_number = models.PositiveIntegerField(default=0)
