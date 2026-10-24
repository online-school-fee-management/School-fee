import csv
import datetime

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from academics.models import AcademicYear, SchoolClass, Student
from accounting.models import CashTransaction
from fees.models import FeeStructure, StudentFee

from .models import Payment
from .services import PaymentError, parse_money, record_payment, void_payment

MANAGE_ROLES = ("admin", "accountant", "teacher")
VIEW_ROLES = ("admin", "accountant", "teacher", "auditor")
MONEY = DecimalField(max_digits=14, decimal_places=2)
STATUSES = ("unpaid", "partial", "paid", "overdue")


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _date(raw):
    try:
        return datetime.date.fromisoformat((raw or "").strip())
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Payment Status (filterable list of every due)
# ---------------------------------------------------------------------------

def _filtered_dues(request):
    """Returns (queryset, filters dict) for the Payment Status page and CSV export."""
    school = request.school
    years = AcademicYear.objects.filter(school=school)

    year_param = request.GET.get("year", "")
    year = None
    if year_param != "all":
        year_id = _to_int(year_param)
        if year_id is None:
            year = years.filter(is_current=True).first() or years.first()
        else:
            year = years.filter(pk=year_id).first()

    class_id = _to_int(request.GET.get("class"))
    fee_type = request.GET.get("type", "")
    title = request.GET.get("fee", "").strip()
    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()
    due_from = _date(request.GET.get("due_from"))
    due_to = _date(request.GET.get("due_to"))

    qs = (
        StudentFee.objects.filter(school=school)
        .select_related("student", "structure", "structure__school_class", "structure__academic_year")
        .annotate(net=ExpressionWrapper(F("amount") - F("waiver"), output_field=MONEY))
    )

    if year:
        qs = qs.filter(structure__academic_year=year)
    if class_id:
        qs = qs.filter(structure__school_class_id=class_id)
    if fee_type in ("annual", "exam"):
        qs = qs.filter(structure__fee_type=fee_type)
    if title:
        qs = qs.filter(structure__title=title)
    if q:
        qs = qs.filter(
            Q(student__name__icontains=q) | Q(student__student_id__icontains=q)
            | Q(student__father_name__icontains=q) | Q(student__phone__icontains=q)
        )
    if due_from:
        qs = qs.filter(structure__due_date__gte=due_from)
    if due_to:
        qs = qs.filter(structure__due_date__lte=due_to)

    today = timezone.localdate()
    if status == "unpaid":
        qs = qs.filter(paid_amount=0, net__gt=0)
    elif status == "partial":
        qs = qs.filter(paid_amount__gt=0, paid_amount__lt=F("net"))
    elif status == "paid":
        qs = qs.filter(paid_amount__gte=F("net"))
    elif status == "overdue":
        qs = qs.filter(paid_amount__lt=F("net"), structure__due_date__lt=today)

    qs = qs.order_by(
        "structure__school_class__order", "structure__school_class__name",
        "student__roll", "student__name", "structure__due_date", "structure__title",
    )

    filters = {
        "years": years, "year": year, "year_all": year_param == "all",
        "class_id": class_id, "fee_type": fee_type, "title": title,
        "status": status if status in STATUSES else "", "q": q,
        "due_from": due_from.isoformat() if due_from else "",
        "due_to": due_to.isoformat() if due_to else "",
        "today": today,
    }
    return qs, filters


@role_required(*VIEW_ROLES)
def payment_status(request):
    school = request.school
    qs, f = _filtered_dues(request)

    totals = qs.aggregate(n=Count("id"), total=Sum("net"), paid=Sum("paid_amount"))
    total = totals["total"] or 0
    paid = totals["paid"] or 0

    page_obj = Paginator(qs, 50).get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    titles = FeeStructure.objects.filter(school=school)
    if f["year"]:
        titles = titles.filter(academic_year=f["year"])
    titles = titles.order_by("title").values_list("title", flat=True).distinct()

    return render(request, "payments/status.html", {
        **f,
        "page_obj": page_obj,
        "classes": SchoolClass.objects.filter(school=school),
        "titles": titles,
        "count": totals["n"],
        "total": total,
        "paid": paid,
        "outstanding": max(total - paid, 0),
        "querystring": params.urlencode(),
    })


@role_required(*VIEW_ROLES)
def payment_export(request):
    qs, _ = _filtered_dues(request)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="payment_status.csv"'
    response.write("\ufeff")  # so Excel reads UTF-8 (Bangla names) correctly

    writer = csv.writer(response)
    writer.writerow([
        "Student ID", "Name", "Class", "Roll", "Fee", "Type", "Academic year",
        "Amount", "Waiver", "Net", "Paid", "Due", "Status", "Due date",
    ])
    for d in qs.iterator():
        writer.writerow([
            d.student.student_id, d.student.name, d.structure.school_class.label,
            d.student.roll if d.student.roll is not None else "",
            d.structure.title, d.structure.get_fee_type_display(),
            d.structure.academic_year.name,
            d.amount, d.waiver, d.net_amount, d.paid_amount, d.due_amount,
            d.status, d.structure.due_date or "",
        ])
    return response


# ---------------------------------------------------------------------------
# Student ledger
# ---------------------------------------------------------------------------

@role_required(*VIEW_ROLES)
def student_ledger(request, student_id):
    school = request.school
    student = get_object_or_404(
        Student.objects.select_related("school_class", "academic_year"),
        pk=student_id, school=school,
    )
    dues = list(
        StudentFee.objects.filter(student=student)
        .select_related("structure", "structure__school_class", "structure__academic_year")
        .order_by("-structure__academic_year__name", "structure__fee_type", "structure__due_date", "structure__title")
    )
    payments = (
        Payment.objects.filter(school=school, student_fee__student=student)
        .select_related("student_fee__structure", "received_by")
    )

    return render(request, "payments/ledger.html", {
        "student": student,
        "dues": dues,
        "payments": payments,
        "total_net": sum(d.net_amount for d in dues),
        "total_paid": sum(d.paid_amount for d in dues),
        "total_due": sum(d.due_amount for d in dues),
        "today": timezone.localdate(),
    })


# ---------------------------------------------------------------------------
# Collect a payment
# ---------------------------------------------------------------------------

@role_required(*MANAGE_ROLES)
def collect(request, pk):
    school = request.school
    fee = get_object_or_404(
        StudentFee.objects.select_related("student", "student__school_class", "structure", "structure__school_class"),
        pk=pk, school=school,
    )
    ledger_url = redirect("payments:student_ledger", student_id=fee.student_id)

    if fee.due_amount <= 0:
        messages.info(request, "This fee is already fully paid.")
        return ledger_url

    errors = []
    if request.method == "POST":
        form = request.POST
        amount = parse_money(request.POST.get("amount"))
        method = request.POST.get("method", "")
        account_type = request.POST.get("account_type", "")
        reference = request.POST.get("reference", "").strip()
        note = request.POST.get("note", "").strip()

        if amount is None:
            errors.append("Enter a valid amount greater than zero.")
        else:
            try:
                payment = record_payment(
                    school=school, fee_id=fee.pk, amount=amount, method=method,
                    reference=reference[:100], note=note[:200], user=request.user,
                    account_type=account_type,
                )
            except PaymentError as exc:
                errors.append(str(exc))
            else:
                messages.success(
                    request, f"Payment of ৳{payment.amount} recorded. Receipt {payment.receipt_no}."
                )
                return redirect("payments:receipt", pk=payment.pk)
    else:
        form = {
            "amount": fee.due_amount,
            "method": Payment.METHOD_CASH,
            "account_type": CashTransaction.ACCOUNT_CASH,
        }

    return render(request, "payments/collect.html", {
        "fee": fee, "form": form, "errors": errors,
        "methods": Payment.METHOD_CHOICES,
        "account_choices": CashTransaction.ACCOUNT_CHOICES,
    })


# ---------------------------------------------------------------------------
# Waiver / void (admin only)
# ---------------------------------------------------------------------------

@role_required("admin")
@require_POST
def set_waiver(request, pk):
    fee = get_object_or_404(StudentFee, pk=pk, school=request.school)
    waiver = parse_money(request.POST.get("waiver"), allow_zero=True)

    if waiver is None:
        messages.error(request, "Enter a valid waiver amount (0 or more).")
    elif waiver > fee.amount:
        messages.error(request, "Waiver cannot be more than the fee amount.")
    elif fee.amount - waiver < fee.paid_amount:
        messages.error(request, "The student has already paid more than the new net amount.")
    else:
        fee.waiver = waiver
        fee.save(update_fields=["waiver"])
        messages.success(request, f"Waiver for '{fee.structure.title}' set to ৳{waiver}.")
    return redirect("payments:student_ledger", student_id=fee.student_id)


@role_required("admin")
@require_POST
def void(request, pk):
    payment = get_object_or_404(Payment, pk=pk, school=request.school)
    student_id = payment.student_fee.student_id
    receipt_no = payment.receipt_no
    void_payment(payment)
    messages.success(request, f"Payment {receipt_no} voided and the amount returned to the due.")
    return redirect("payments:student_ledger", student_id=student_id)


# ---------------------------------------------------------------------------
# Receipt (printable page). Staff can open any; a student only their own.
# ---------------------------------------------------------------------------

def receipt(request, pk):
    user = request.user
    if not user.is_authenticated:
        return redirect_to_login(request.get_full_path())

    school = getattr(request, "school", None)
    if school is None or user.school_id != school.id:
        return HttpResponseForbidden("Access denied for this school.")

    payment = get_object_or_404(
        Payment.objects.select_related(
            "student_fee", "student_fee__student", "student_fee__student__school_class",
            "student_fee__structure", "student_fee__structure__school_class",
            "student_fee__structure__academic_year", "received_by",
        ),
        pk=pk, school=school,
    )

    allowed = user.role in VIEW_ROLES or (
        user.role == "student" and payment.student_fee.student.user_id == user.id
    )
    if not allowed:
        return HttpResponseForbidden("You do not have permission.")

    return render(request, "payments/receipt.html", {
        "payment": payment,
        "fee": payment.student_fee,
        "student": payment.student_fee.student,
        "school": school,
    })
