import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, DecimalField, ExpressionWrapper, F, ProtectedError, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from academics.models import AcademicYear, SchoolClass

from .models import FeeStructure, StudentFee
from .services import generate_dues, missing_students_count

ROLES = ("admin", "accountant")
TYPES = {value for value, _ in FeeStructure.TYPE_CHOICES}
MONEY = DecimalField(max_digits=14, decimal_places=2)


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_amount(raw):
    try:
        amount = Decimal((raw or "").strip())
    except InvalidOperation:
        return None
    if not amount.is_finite() or amount <= 0 or amount > Decimal("99999999"):
        return None
    return amount.quantize(Decimal("0.01"))


def _parse_date(raw):
    raw = (raw or "").strip()
    if not raw:
        return None, True
    try:
        return datetime.date.fromisoformat(raw), True
    except ValueError:
        return None, False


def _list_url(year=None):
    url = reverse("fees:fee_list")
    return f"{url}?year={year.pk}" if year else url


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@role_required(*ROLES)
def fee_list(request):
    school = request.school
    years = AcademicYear.objects.filter(school=school)

    year_id = _to_int(request.GET.get("year"))
    if year_id is None:
        year = years.filter(is_current=True).first() or years.first()
    else:
        year = years.filter(pk=year_id).first()

    class_id = _to_int(request.GET.get("class"))
    fee_type = request.GET.get("type", "")

    structures = []
    if year:
        qs = FeeStructure.objects.filter(school=school, academic_year=year).select_related(
            "school_class", "academic_year"
        )
        if class_id:
            qs = qs.filter(school_class_id=class_id)
        if fee_type in TYPES:
            qs = qs.filter(fee_type=fee_type)

        qs = qs.annotate(
            dues_count=Count("student_fees"),
            total_net=Sum(
                ExpressionWrapper(F("student_fees__amount") - F("student_fees__waiver"), output_field=MONEY)
            ),
            collected=Sum("student_fees__paid_amount"),
        )
        structures = list(qs)
        for s in structures:
            s.missing = missing_students_count(s)

    return render(request, "fees/fees.html", {
        "years": years,
        "year": year,
        "classes": SchoolClass.objects.filter(school=school),
        "class_id": class_id,
        "fee_type": fee_type,
        "structures": structures,
        "any_missing": any(s.missing for s in structures),
    })


# ---------------------------------------------------------------------------
# Add (one fee -> many classes at once)
# ---------------------------------------------------------------------------

@role_required(*ROLES)
def fee_add(request):
    school = request.school
    classes = SchoolClass.objects.filter(school=school)
    years = AcademicYear.objects.filter(school=school)
    errors = []
    selected = set()

    if request.method == "POST":
        form = request.POST
        selected = set(request.POST.getlist("classes"))

        fee_type = request.POST.get("fee_type", "")
        title = request.POST.get("title", "").strip()
        year = years.filter(pk=_to_int(request.POST.get("academic_year"))).first()
        class_objs = list(classes.filter(pk__in=[_to_int(c) for c in selected if _to_int(c)]))
        amount = _parse_amount(request.POST.get("amount"))
        due_date, date_ok = _parse_date(request.POST.get("due_date"))
        generate_now = request.POST.get("generate_now") == "on"

        if fee_type not in TYPES:
            errors.append("Please select a fee type.")
        if not title:
            errors.append("Fee title is required.")
        elif len(title) > 100:
            errors.append("Fee title is too long.")
        if year is None:
            errors.append("Please select an academic year.")
        if not class_objs:
            errors.append("Select at least one class.")
        if amount is None:
            errors.append("Enter a valid amount greater than zero.")
        if not date_ok:
            errors.append("Invalid due date.")

        if not errors:
            created, skipped, dues = 0, [], 0
            with transaction.atomic():
                for c in class_objs:
                    obj, was_created = FeeStructure.objects.get_or_create(
                        school=school, academic_year=year, school_class=c, title=title,
                        defaults={"fee_type": fee_type, "amount": amount, "due_date": due_date},
                    )
                    if was_created:
                        created += 1
                        if generate_now:
                            dues += generate_dues(obj)
                    else:
                        skipped.append(c.label)

            if created:
                msg = f"'{title}' added for {created} class(es)."
                if generate_now:
                    msg += f" {dues} student dues created."
                messages.success(request, msg)
            if skipped:
                messages.warning(request, "Already existed, skipped: " + ", ".join(skipped))
            if created or skipped:
                return redirect(_list_url(year))
    else:
        current = years.filter(is_current=True).first()
        form = {
            "fee_type": "annual",
            "academic_year": str(current.pk) if current else "",
            "generate_now": "on",
        }

    return render(request, "fees/fee_form.html", {
        "form": form, "errors": errors, "classes": classes, "years": years,
        "selected": selected, "type_choices": FeeStructure.TYPE_CHOICES,
    })


# ---------------------------------------------------------------------------
# Edit / delete / generate
# ---------------------------------------------------------------------------

@role_required(*ROLES)
def fee_edit(request, pk):
    school = request.school
    fee = get_object_or_404(
        FeeStructure.objects.select_related("school_class", "academic_year"),
        pk=pk, school=school,
    )
    errors = []

    if request.method == "POST":
        form = request.POST
        fee_type = request.POST.get("fee_type", "")
        title = request.POST.get("title", "").strip()
        amount = _parse_amount(request.POST.get("amount"))
        due_date, date_ok = _parse_date(request.POST.get("due_date"))

        if fee_type not in TYPES:
            errors.append("Please select a fee type.")
        if not title:
            errors.append("Fee title is required.")
        elif len(title) > 100:
            errors.append("Fee title is too long.")
        elif FeeStructure.objects.filter(
            school=school, academic_year=fee.academic_year,
            school_class=fee.school_class, title=title,
        ).exclude(pk=fee.pk).exists():
            errors.append(f"'{title}' already exists for this class and year.")
        if amount is None:
            errors.append("Enter a valid amount greater than zero.")
        if not date_ok:
            errors.append("Invalid due date.")

        if not errors:
            with transaction.atomic():
                fee.fee_type = fee_type
                fee.title = title
                fee.amount = amount
                fee.due_date = due_date
                fee.is_active = request.POST.get("is_active") == "on"
                fee.save()
                updated = 0
                if request.POST.get("update_unpaid") == "on":
                    # Only dues with no payment yet are changed.
                    updated = StudentFee.objects.filter(
                        structure=fee, paid_amount=0
                    ).update(amount=amount)
            msg = "Fee updated."
            if updated:
                msg += f" {updated} unpaid dues set to the new amount."
            messages.success(request, msg)
            return redirect(_list_url(fee.academic_year))
    else:
        form = {
            "fee_type": fee.fee_type, "title": fee.title, "amount": fee.amount,
            "due_date": fee.due_date.isoformat() if fee.due_date else "",
            "is_active": "on" if fee.is_active else "",
        }

    return render(request, "fees/fee_edit.html", {
        "fee": fee, "form": form, "errors": errors,
        "type_choices": FeeStructure.TYPE_CHOICES,
        "paid_count": StudentFee.objects.filter(structure=fee, paid_amount__gt=0).count(),
    })


@role_required(*ROLES)
@require_POST
def fee_delete(request, pk):
    fee = get_object_or_404(FeeStructure, pk=pk, school=request.school)
    year = fee.academic_year

    if StudentFee.objects.filter(structure=fee, paid_amount__gt=0).exists():
        messages.error(
            request,
            "Some students have already paid this fee, so it cannot be deleted. "
            "You can deactivate it from Edit instead.",
        )
        return redirect(_list_url(year))

    try:
        removed = StudentFee.objects.filter(structure=fee).count()
        fee.delete()
        messages.success(request, f"'{fee.title}' deleted ({removed} unpaid dues removed).")
    except ProtectedError:
        messages.error(request, "This fee is in use and cannot be deleted.")
    return redirect(_list_url(year))


@role_required(*ROLES)
@require_POST
def fee_generate(request, pk):
    fee = get_object_or_404(FeeStructure, pk=pk, school=request.school)
    if not fee.is_active:
        messages.error(request, "This fee is inactive. Activate it first.")
    else:
        count = generate_dues(fee)
        messages.success(request, f"{count} new student dues created for '{fee.title}'.")
    return redirect(_list_url(fee.academic_year))


@role_required(*ROLES)
@require_POST
def fee_generate_all(request):
    school = request.school
    year = get_object_or_404(AcademicYear, pk=_to_int(request.POST.get("year")), school=school)
    total = 0
    with transaction.atomic():
        for fee in FeeStructure.objects.filter(school=school, academic_year=year, is_active=True):
            total += generate_dues(fee)
    messages.success(request, f"{total} new student dues created for {year.name}.")
    return redirect(_list_url(year))
