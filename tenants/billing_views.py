import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.decorators import role_required

from . import billing, plans
from .models import SubscriptionPayment


def demo_enabled():
    """
    The demo payment switches a paid plan on WITHOUT real money, so it is on only
    while DEBUG is on. In production set ALLOW_DEMO_SUBSCRIPTIONS = False (or leave
    DEBUG off) until a real gateway is connected; then you assign plans from the
    owner panel after a school pays you.
    """
    return getattr(settings, "ALLOW_DEMO_SUBSCRIPTIONS", settings.DEBUG)


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@role_required("admin")
def plans_page(request):
    school = request.school
    months = _to_int(request.GET.get("months"))
    if months not in plans.DURATIONS:
        months = 1

    cards = []
    for key, cfg in billing.purchasable_plans():
        total = plans.price_for(key, months)
        full_price = Decimal(cfg["price_monthly"]) * months
        cards.append({
            "key": key,
            "label": cfg["label"],
            "student_limit": cfg.get("student_limit"),
            "staff_limit": cfg.get("staff_limit"),
            "online_payments": cfg.get("online_payments"),
            "price": total,
            "saving": full_price - total if full_price > total else None,
            "current": key == school.effective_plan,
            "allowed": billing.can_buy(school, key),
        })

    return render(request, "billing/plans.html", {
        "cards": cards,
        "months": months,
        "durations": [(key, d["label"]) for key, d in plans.DURATIONS.items()],
        "info": school.plan_info,
        "plan_expires_at": school.plan_expires_at,
        "demo_enabled": demo_enabled(),
    })


@role_required("admin")
def checkout(request):
    school = request.school
    source = request.POST if request.method == "POST" else request.GET
    plan_key = source.get("plan", "")
    months = _to_int(source.get("months"))

    amount = plans.price_for(plan_key, months)
    if amount is None or not billing.can_buy(school, plan_key):
        messages.error(request, "That plan or duration is not available.")
        return redirect("billing:plans")

    cfg = plans.get_plan(plan_key)

    if request.method == "POST":
        # One-time token: a double click or a page refresh cannot pay twice.
        if request.POST.get("token") != request.session.pop("checkout_token", None):
            messages.error(request, "This checkout was already used or has expired. Please start again.")
            return redirect("billing:plans")

        if not demo_enabled() or request.POST.get("gateway") != "demo":
            messages.error(request, "Online payment is not available right now. Please contact us.")
            return redirect("billing:plans")

        try:
            payment = billing.activate_plan_demo(
                school=school, plan_key=plan_key, months=months, user=request.user,
            )
        except billing.BillingError as exc:
            messages.error(request, str(exc))
            return redirect("billing:plans")

        messages.success(
            request,
            f"Payment successful. Your school is now on the {payment.plan_label} plan "
            f"until {timezone.localtime(payment.period_end).strftime('%d %b %Y')}.",
        )
        return redirect("billing:invoice", pk=payment.pk)

    token = uuid.uuid4().hex
    request.session["checkout_token"] = token
    start, end = billing.new_period(school, plan_key, months)

    return render(request, "billing/checkout.html", {
        "plan_key": plan_key,
        "plan_label": cfg["label"],
        "student_limit": cfg.get("student_limit"),
        "staff_limit": cfg.get("staff_limit"),
        "online_payments": cfg.get("online_payments"),
        "months": months,
        "duration_label": plans.DURATIONS[months]["label"],
        "amount": amount,
        "period_start": start,
        "period_end": end,
        "is_renewal": school.effective_plan == plan_key,
        "current_label": school.effective_plan_label,
        "token": token,
        "demo_enabled": demo_enabled(),
    })


@role_required("admin")
def history(request):
    return render(request, "billing/history.html", {
        "payments": SubscriptionPayment.objects.filter(school=request.school),
    })


@role_required("admin")
def invoice(request, pk):
    payment = get_object_or_404(SubscriptionPayment, pk=pk, school=request.school)
    return render(request, "billing/invoice.html", {
        "payment": payment, "school": request.school,
    })
