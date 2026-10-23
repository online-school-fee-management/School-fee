from django.conf import settings

# ---------------------------------------------------------------------------
# PLAN SETTINGS - change the numbers here whenever you decide your pricing.
# (Or put your own PLANS = {...} / TRIAL_DAYS = 30 in settings.py to override.)
#
#   student_limit    : most student records a school can have. None = unlimited.
#   staff_limit      : most ACTIVE staff logins (admin + accountant + teacher). None = unlimited.
#   online_payments  : can students pay from the student portal?
#
# New schools start on "trial". When a trial or paid plan runs out, the school
# drops to "free". Nothing is deleted or locked: the school keeps all its data
# and can still collect fees, it just cannot add students or staff above the
# free limits.
# ---------------------------------------------------------------------------
DEFAULT_PLANS = {
    "trial":    {"label": "Free trial", "student_limit": 500,  "staff_limit": 10,   "online_payments": True},
    "free":     {"label": "Free",       "student_limit": 50,   "staff_limit": 2,    "online_payments": False},
    "basic":    {"label": "Basic",      "student_limit": 300,  "staff_limit": 5,    "online_payments": True},
    "standard": {"label": "Standard",   "student_limit": 1000, "staff_limit": 15,   "online_payments": True},
    "premium":  {"label": "Premium",    "student_limit": None, "staff_limit": None, "online_payments": True},
}
DEFAULT_TRIAL_DAYS = 30


def get_plans():
    return getattr(settings, "PLANS", DEFAULT_PLANS)


def get_plan(key):
    """Config of one plan; unknown keys fall back to 'free'."""
    plans = get_plans()
    return plans.get(key) or plans.get("free") or DEFAULT_PLANS["free"]


def get_trial_days():
    return getattr(settings, "TRIAL_DAYS", DEFAULT_TRIAL_DAYS)
