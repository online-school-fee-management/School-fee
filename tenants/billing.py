import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from . import plans
from .models import School, SubscriptionPayment

# Higher number = bigger plan. Used so nobody pays to move to a smaller plan by mistake.
PLAN_RANK = {"free": 0, "trial": 1, "basic": 2, "standard": 3, "premium": 4}


class BillingError(Exception):
    """Message is safe to show to the user."""


def purchasable_plans():
    """[(key, config)] of every plan that has a price."""
    return [(key, cfg) for key, cfg in plans.get_plans().items() if cfg.get("price_monthly")]


def can_buy(school, plan_key):
    cfg = plans.get_plans().get(plan_key)
    if not cfg or not cfg.get("price_monthly"):
        return False

    current = school.effective_plan
    if current in ("free", "trial"):
        return True
    if plan_key == current and school.plan_expires_at is None:
        return False  # a plan with no end date has nothing to renew
    return PLAN_RANK.get(plan_key, 0) >= PLAN_RANK.get(current, 0)


def new_period(school, plan_key, months):
    """
    (start, end) of the period being bought.
      - Renewing the plan the school already has: time is added after the current end date.
      - Anything else (first purchase, or upgrading): starts now. Time left on the old
        plan is not carried over.
    """
    now = timezone.now()
    start = now
    if (school.effective_plan == plan_key and school.plan_expires_at
            and school.plan_expires_at > now):
        start = school.plan_expires_at
    return start, start + timedelta(days=plans.DURATIONS[months]["days"])


@transaction.atomic
def activate_plan_demo(*, school, plan_key, months, user):
    """
    DEMO payment: no real money moves. Records the payment and switches the plan on.
    A real gateway (e.g. bKash) will do the same thing, but only after the gateway
    confirms the money was received.
    """
    school = School.objects.select_for_update().get(pk=school.pk)

    amount = plans.price_for(plan_key, months)
    if amount is None or not can_buy(school, plan_key):
        raise BillingError("That plan is not available for your school right now.")

    start, end = new_period(school, plan_key, months)
    payment = SubscriptionPayment.objects.create(
        school=school, plan=plan_key, months=months, amount=amount,
        method=SubscriptionPayment.METHOD_DEMO,
        reference="DEMO-" + uuid.uuid4().hex[:12].upper(),
        period_start=start, period_end=end, paid_by=user,
    )
    school.plan = plan_key
    school.plan_expires_at = end
    school.save(update_fields=["plan", "plan_expires_at"])
    return payment
