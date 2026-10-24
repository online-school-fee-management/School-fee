from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from tenants.models import SchoolOwnedModel


class AccountingSettings(models.Model):
    """One simple cash-book setup per school."""

    school = models.OneToOneField(
        "tenants.School", on_delete=models.CASCADE, related_name="accounting_settings"
    )
    opening_cash = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Opening cash at hand",
    )
    opening_bank = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Opening cash at bank",
    )
    opening_date = models.DateField(
        default=timezone.localdate,
        verbose_name="Cash book starts on",
        help_text="The opening balances are the amounts already in each account on this date.",
    )
    bank_name = models.CharField(max_length=120, blank=True)
    bank_account_number = models.CharField(
        max_length=60, blank=True, verbose_name="Bank account number"
    )
    last_receipt_number = models.PositiveIntegerField(default=0)
    last_payment_number = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Accounting setup - {self.school.name}"

    @property
    def bank_label(self):
        return self.bank_name or "Cash at Bank"


class CashTransaction(SchoolOwnedModel):
    """A receipt (money in) or payment (money out), recorded on a cash basis."""

    TYPE_RECEIPT = "receipt"
    TYPE_PAYMENT = "payment"
    TYPE_CHOICES = [
        (TYPE_RECEIPT, "Receipt - money received"),
        (TYPE_PAYMENT, "Payment - money paid"),
    ]

    ACCOUNT_CASH = "cash"
    ACCOUNT_BANK = "bank"
    ACCOUNT_CHOICES = [
        (ACCOUNT_CASH, "Cash at Hand"),
        (ACCOUNT_BANK, "Cash at Bank"),
    ]

    CATEGORY_STUDENT_FEES = "student_fees"
    CATEGORY_CHOICES = [
        (CATEGORY_STUDENT_FEES, "Student fees"),
        ("admission_fees", "Admission fees"),
        ("donation", "Donation"),
        ("grant", "Grant or aid"),
        ("sale", "Sale of goods"),
        ("other_income", "Other income"),
        ("salary", "Salary"),
        ("rent", "Rent"),
        ("utilities", "Utilities"),
        ("supplies", "Supplies"),
        ("maintenance", "Repairs and maintenance"),
        ("transport", "Transport"),
        ("event", "Event expense"),
        ("tax", "Tax and government fees"),
        ("other_expense", "Other expense"),
    ]

    SOURCE_MANUAL = "manual"
    SOURCE_STUDENT_FEE = "student_fee"
    SOURCE_CHOICES = [
        (SOURCE_MANUAL, "Entered in accounting"),
        (SOURCE_STUDENT_FEE, "Student fee collection"),
    ]

    voucher_no = models.CharField(max_length=20, blank=True)
    entry_date = models.DateField(default=timezone.localdate)
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_CHOICES)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    party = models.CharField(
        max_length=180, verbose_name="Received from / paid to"
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    reference = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default=SOURCE_MANUAL
    )
    source_payment = models.OneToOneField(
        "payments.Payment",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="accounting_entry",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_voided = models.BooleanField(default=False)
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    void_reason = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ["-entry_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "voucher_no"],
                name="uniq_accounting_voucher_per_school",
            )
        ]

    def __str__(self):
        return f"{self.voucher_no} - {self.party} - {self.amount}"

    @property
    def signed_amount(self):
        if self.transaction_type == self.TYPE_RECEIPT:
            return self.amount
        return -self.amount

    @property
    def account_label(self):
        return "Cash at Hand" if self.account_type == self.ACCOUNT_CASH else "Cash at Bank"

    @property
    def document_label(self):
        return "Receipt voucher" if self.transaction_type == self.TYPE_RECEIPT else "Payment voucher"
