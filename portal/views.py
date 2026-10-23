import datetime
import uuid
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import role_required
from fees.models import StudentFee
from payments.models import Payment
from payments.services import PaymentError, parse_money, record_payment


def test_payments_enabled():
    """
    The "test payment" marks a fee as paid WITHOUT real money, so it is on only
    while DEBUG is on. In production set ALLOW_TEST_PAYMENTS = False (or leave
    DEBUG off) until a real gateway such as bKash is connected.
    """
    return getattr(settings, "ALLOW_TEST_PAYMENTS", settings.DEBUG)


def student_view(view):
    """Student role only, and the logged-in user must have a Student record."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        student = getattr(request.user, "student_profile", None)
        if student is None:
            return render(request, "portal/no_profile.html", status=403)
        return view(request, student, *args, **kwargs)

    return role_required("student")(wrapper)


def _all_dues(student):
    dues = list(
        StudentFee.objects.filter(student=student).select_related(
            "structure", "structure__school_class", "structure__academic_year"
        )
    )
    # soonest due date first; fees with no due date last
    dues.sort(key=lambda d: (
        d.structure.due_date is None,
        d.structure.due_date or datetime.date.max,
        d.structure.title,
    ))
    return dues


def _my_payments(request, student):
    return Payment.objects.filter(
        school=request.school, student_fee__student=student
    ).select_related("student_fee__structure")


@student_view
def home(request, student):
    dues = _all_dues(student)
    unpaid = [d for d in dues if d.due_amount > 0]
    today = timezone.localdate()

    return render(request, "portal/home.html", {
        "student": student,
        "total_due": sum(d.due_amount for d in dues),
        "total_paid": sum(d.paid_amount for d in dues),
        "unpaid_count": len(unpaid),
        "overdue_count": sum(
            1 for d in unpaid if d.structure.due_date and d.structure.due_date < today
        ),
        "next_due": unpaid[0] if unpaid else None,
        "recent": _my_payments(request, student)[:3],
        "today": today,
    })


@student_view
def dues(request, student):
    show = request.GET.get("show", "due")
    items = _all_dues(student)
    if show != "all":
        items = [d for d in items if d.due_amount > 0]

    return render(request, "portal/dues.html", {
        "student": student,
        "dues": items,
        "show": "all" if show == "all" else "due",
        "total_due": sum(d.due_amount for d in items if d.due_amount > 0),
        "today": timezone.localdate(),
    })


@student_view
def pay(request, student, pk):
    # A student can only ever open their own dues.
    fee = get_object_or_404(
        StudentFee.objects.select_related(
            "structure", "structure__school_class", "structure__academic_year"
        ),
        pk=pk, school=request.school, student=student,
    )

    if fee.due_amount <= 0:
        messages.info(request, "This fee is already fully paid.")
        return redirect("portal:dues")

    enabled = test_payments_enabled()

    if request.method == "POST":
        if not enabled or request.POST.get("gateway") != "test":
            messages.error(request, "Online payment is not available right now.")
            return redirect("portal:pay", pk=fee.pk)

        # The amount is always the full due, checked again on the server.
        if parse_money(request.POST.get("amount")) != fee.due_amount:
            messages.error(request, "The amount due has changed. Please check and try again.")
            return redirect("portal:pay", pk=fee.pk)

        try:
            payment = record_payment(
                school=request.school, fee_id=fee.pk, amount=fee.due_amount,
                method=Payment.METHOD_ONLINE,
                reference="TEST-" + uuid.uuid4().hex[:12].upper(),
                note="Student portal (test payment)",
                user=None, online=True,
            )
        except PaymentError as exc:
            messages.error(request, str(exc))
            return redirect("portal:dues")

        messages.success(
            request, f"Payment of ৳{payment.amount} successful. Receipt {payment.receipt_no}."
        )
        return redirect("payments:receipt", pk=payment.pk)

    return render(request, "portal/pay.html", {
        "student": student, "fee": fee, "test_enabled": enabled,
    })


@student_view
def history(request, student):
    page_obj = Paginator(_my_payments(request, student), 25).get_page(request.GET.get("page"))
    return render(request, "portal/history.html", {
        "student": student, "page_obj": page_obj,
    })
