from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from .models import AccountingSettings, CashTransaction


def get_settings(school):
    return AccountingSettings.objects.get_or_create(school=school)[0]


def _next_voucher(settings, transaction_type):
    if transaction_type == CashTransaction.TYPE_RECEIPT:
        settings.last_receipt_number += 1
        number = settings.last_receipt_number
        prefix = "RV"
    else:
        settings.last_payment_number += 1
        number = settings.last_payment_number
        prefix = "PV"
    settings.save(update_fields=["last_receipt_number", "last_payment_number"])
    return f"{prefix}-{number:06d}"


@transaction.atomic
def create_transaction(
    *,
    school,
    transaction_type,
    account_type,
    category,
    party,
    amount,
    entry_date=None,
    reference="",
    description="",
    created_by=None,
    source=CashTransaction.SOURCE_MANUAL,
    source_payment=None,
):
    settings = AccountingSettings.objects.select_for_update().get_or_create(
        school=school
    )[0]
    if source_payment is not None:
        existing = CashTransaction.objects.filter(source_payment=source_payment).first()
        if existing:
            return existing

    return CashTransaction.objects.create(
        school=school,
        voucher_no=_next_voucher(settings, transaction_type),
        transaction_type=transaction_type,
        account_type=account_type,
        category=category,
        party=party[:180],
        amount=amount,
        entry_date=entry_date or timezone.localdate(),
        reference=reference[:120],
        description=description,
        created_by=created_by,
        source=source,
        source_payment=source_payment,
    )


def post_fee_payment(payment, account_type=None):
    """
    Add a collected student fee to the cash book.
    The temporary online test method is intentionally excluded because no real
    money moves through it.
    """
    if payment.method == "online":
        return None
    if account_type not in (
        CashTransaction.ACCOUNT_CASH,
        CashTransaction.ACCOUNT_BANK,
    ):
        account_type = (
            CashTransaction.ACCOUNT_CASH
            if payment.method == "cash"
            else CashTransaction.ACCOUNT_BANK
        )
    fee = payment.student_fee
    return create_transaction(
        school=payment.school,
        transaction_type=CashTransaction.TYPE_RECEIPT,
        account_type=account_type,
        category=CashTransaction.CATEGORY_STUDENT_FEES,
        party=fee.student.name,
        amount=payment.amount,
        entry_date=timezone.localdate(payment.paid_at),
        reference=payment.reference or payment.receipt_no,
        description=(
            f"{fee.structure.title} | {fee.student.student_id} | "
            f"{fee.student.school_class.label}"
        ),
        created_by=payment.received_by,
        source=CashTransaction.SOURCE_STUDENT_FEE,
        source_payment=payment,
    )


def account_balance(school, account_type, as_of=None, settings_obj=None):
    settings_obj = settings_obj or get_settings(school)
    as_of = as_of or timezone.localdate()
    qs = CashTransaction.objects.filter(
        school=school,
        account_type=account_type,
        is_voided=False,
    )
    qs = qs.filter(entry_date__lte=as_of)
    totals = qs.aggregate(
        receipts=Sum(
            "amount",
            filter=Q(transaction_type=CashTransaction.TYPE_RECEIPT),
        ),
        payments=Sum(
            "amount",
            filter=Q(transaction_type=CashTransaction.TYPE_PAYMENT),
        ),
    )
    opening = (
        settings_obj.opening_cash
        if account_type == CashTransaction.ACCOUNT_CASH
        else settings_obj.opening_bank
    )
    return opening + (totals["receipts"] or Decimal("0.00")) - (
        totals["payments"] or Decimal("0.00")
    )


def ledger_for(school, account_type, date_from, date_to):
    settings_obj = get_settings(school)
    base = CashTransaction.objects.filter(
        school=school,
        account_type=account_type,
        is_voided=False,
    )
    before = base.filter(entry_date__lt=date_from).aggregate(
        receipts=Sum(
            "amount",
            filter=Q(transaction_type=CashTransaction.TYPE_RECEIPT),
        ),
        payments=Sum(
            "amount",
            filter=Q(transaction_type=CashTransaction.TYPE_PAYMENT),
        ),
    )
    opening_balance = (
        (
            settings_obj.opening_cash
            if account_type == CashTransaction.ACCOUNT_CASH
            else settings_obj.opening_bank
        )
        + (before["receipts"] or Decimal("0.00"))
        - (before["payments"] or Decimal("0.00"))
    )
    entries = list(
        base.filter(entry_date__gte=date_from, entry_date__lte=date_to)
        .select_related("created_by", "voided_by", "source_payment")
        .order_by("entry_date", "id")
    )
    running = opening_balance
    period_receipts = Decimal("0.00")
    period_payments = Decimal("0.00")
    for entry in entries:
        running += entry.signed_amount
        entry.running_balance = running
        if entry.transaction_type == CashTransaction.TYPE_RECEIPT:
            period_receipts += entry.amount
        else:
            period_payments += entry.amount
    return {
        "settings": settings_obj,
        "entries": entries,
        "opening_balance": opening_balance,
        "period_receipts": period_receipts,
        "period_payments": period_payments,
        "closing_balance": opening_balance + period_receipts - period_payments,
    }
