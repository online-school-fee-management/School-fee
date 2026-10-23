import datetime
from datetime import timedelta

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from . import plans
from .models import School
from .owner_views import owner_required


@owner_required
def owner_plan(request, pk):
    """Owner assigns a plan to a school (after the school has paid you)."""
    school = get_object_or_404(School, pk=pk)
    available = plans.get_plans()
    errors = []

    if request.method == "POST":
        plan = request.POST.get("plan", "")
        raw_date = request.POST.get("expires", "").strip()
        expires_at = None

        if plan not in available:
            errors.append("Please choose a plan.")
        if raw_date:
            try:
                day = datetime.date.fromisoformat(raw_date)
            except ValueError:
                errors.append("Invalid date.")
            else:
                # valid until the END of that day
                expires_at = timezone.make_aware(
                    datetime.datetime.combine(day, datetime.time(23, 59, 59))
                )

        if not errors:
            if plan == "free":
                expires_at = None  # the free plan never expires
            elif plan == "trial" and expires_at is None:
                expires_at = timezone.now() + timedelta(days=plans.get_trial_days())

            school.plan = plan
            school.plan_expires_at = expires_at
            school.save(update_fields=["plan", "plan_expires_at"])
            messages.success(request, f"{school.name} is now on the {plans.get_plan(plan)['label']} plan.")

            next_url = request.POST.get("next", "")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect("tenants:owner")

        form = request.POST
    else:
        form = {
            "plan": school.plan,
            "expires": timezone.localtime(school.plan_expires_at).date().isoformat()
            if school.plan_expires_at else "",
        }

    return render(request, "tenants/owner_plan.html", {
        "school": school,
        "form": form,
        "errors": errors,
        "plan_list": [
            {
                "key": key,
                "label": cfg["label"],
                "student_limit": cfg.get("student_limit"),
                "staff_limit": cfg.get("staff_limit"),
                "online_payments": cfg.get("online_payments"),
            }
            for key, cfg in available.items()
        ],
        "info": school.plan_info,
        "next": request.GET.get("next", ""),
        "trial_days": plans.get_trial_days(),
    })
