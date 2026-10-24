from decimal import Decimal, InvalidOperation

from django.db import transaction

from fees.models import StudentFee

from .models import Payment, ReceiptSequence

METHODS = {value for value, _ in Payment.METHOD_CHOICES}


class PaymentError(Exception):
    """Raised with a message that is safe to show to the user."""


def parse_money(raw, allow_zero=False):
    """'1500' -> Decimal('1500.00'); returns None if invalid."""
    try:
        value = Decimal((raw or "").strip())
    except InvalidOperation:
        return None
    if not value.is_finite() or value > Decimal("99999999"):
        return None
    if value < 0 or (value == 0 and not allow_zero):
        return None
    return value.quantize(Decimal("0.01"))


def next_receipt_no(school):
    """Must be called inside transaction.atomic()."""
    seq, _ = ReceiptSequence.objects.select_for_update().get_or_create(school=school)
    seq.last_number += 1
    seq.save(update_fields=["last_number"])
    return f"R{seq.last_number:06d}"


@transaction.atomic
def record_payment(
    *,
    school,
    fee_id,
    amount,
    method,
    reference,
    note,
    user,
    online=False,
    account_type=None,
):
    """
    Add a payment to a student's due and update the due's paid_amount.
    The due row is locked, so two payments cannot overpay the same due.

    online=True is passed only by the student portal; staff screens leave it
    False, so staff cannot record a payment with the "online" method by hand.
    """
    fee = StudentFee.objects.select_for_update().get(pk=fee_id, school=school)

    if method not in METHODS:
        raise PaymentError("Please choose a payment method.")
    if method == Payment.METHOD_ONLINE and not online:
        raise PaymentError("This method can only be used for online payments.")
    if method != Payment.METHOD_CASH and not reference:
        raise PaymentError("Transaction ID / reference is required for this method.")
    if amount > fee.due_amount:
        raise PaymentError(f"Amount is more than the due (৳{fee.due_amount}).")

    payment = Payment.objects.create(
        school=school,
        student_fee=fee,
        amount=amount,
        method=method,
        reference=reference,
        note=note,
        receipt_no=next_receipt_no(school),
        received_by=user,
    )
    fee.paid_amount += amount
    fee.save(update_fields=["paid_amount"])

    # Keep the simple cash-book ledger in step with fee collections. The
    # temporary online test method is skipped inside post_fee_payment.
    from accounting.services import post_fee_payment

    post_fee_payment(payment, account_type=account_type)
    return payment


@transaction.atomic
def void_payment(payment):
    """Delete a wrongly recorded payment and give the amount back to the due."""
    fee = StudentFee.objects.select_for_update().get(pk=payment.student_fee_id)
    fee.paid_amount = max(fee.paid_amount - payment.amount, Decimal("0.00"))
    fee.save(update_fields=["paid_amount"])
    payment.delete()
