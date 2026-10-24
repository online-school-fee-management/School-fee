from decimal import Decimal

from django.conf import settings

# ---------------------------------------------------------------------------
# PLAN SETTINGS - change the numbers here whenever you decide your pricing.
# (Or put your own PLANS = {...} / TRIAL_DAYS = 30 in settings.py to override.)
#
#   student_limit    : most student records a school can have. None = unlimited.
#   staff_limit      : most ACTIVE staff logins (every non-student role). None = unlimited.
#   online_payments  : can students pay from the student portal?
#   price_monthly    : price in taka per month. None = cannot be bought (trial / free).
#
# The prices below are PLACEHOLDERS. Set your real prices before going live.
#
# New schools start on "trial". When a trial or paid plan runs out, the school
# drops to "free". Nothing is deleted or locked: the school keeps all its data
# and can still collect fees, it just cannot add students or staff above the
# free limits.
# ---------------------------------------------------------------------------
DEFAULT_PLANS = {
    "trial":    {"label": "Free trial", "student_limit": 500,  "staff_limit": 10,   "online_payments": True,  "price_monthly": None},
    "free":     {"label": "Free",       "student_limit": 50,   "staff_limit": 2,    "online_payments": False, "price_monthly": None},
    "basic":    {"label": "Basic",      "student_limit": 300,  "staff_limit": 5,    "online_payments": True,  "price_monthly": 500},
    "standard": {"label": "Standard",   "student_limit": 1000, "staff_limit": 15,   "online_payments": True,  "price_monthly": 1500},
    "premium":  {"label": "Premium",    "student_limit": None, "staff_limit": None, "online_payments": True,  "price_monthly": 3000},
}
DEFAULT_TRIAL_DAYS = 30

# How long a purchase lasts, and how many months you are charged for it.
# 12 months = pay for 10 (two months free). Change freely.
DURATIONS = {
    1:  {"label": "1 month",   "days": 30,  "charged_months": 1},
    12: {"label": "12 months", "days": 365, "charged_months": 10},
}


def get_plans():
    return getattr(settings, "PLANS", DEFAULT_PLANS)


def get_plan(key):
    """Config of one plan; unknown keys fall back to 'free'."""
    plans = get_plans()
    return plans.get(key) or plans.get("free") or DEFAULT_PLANS["free"]


def get_trial_days():
    return getattr(settings, "TRIAL_DAYS", DEFAULT_TRIAL_DAYS)


def price_for(plan_key, months):
    """Total price (Decimal) of a plan for 1 or 12 months, or None if it cannot be bought."""
    cfg = get_plans().get(plan_key)
    duration = DURATIONS.get(months)
    if not cfg or not duration or not cfg.get("price_monthly"):
        return None
    return (Decimal(cfg["price_monthly"]) * duration["charged_months"]).quantize(Decimal("0.01"))
