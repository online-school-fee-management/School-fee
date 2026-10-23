import csv
from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q, Sum
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from academics.models import Student
from payments.models import Payment

from .models import School
from .views import school_url

User = get_user_model()


def owner_required(view):
    """Platform owner only: a superuser, on the main domain (no school subdomain)."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if getattr(request, "school", None) is not None:
            return HttpResponseForbidden("The owner panel is only on the main domain.")
        user = request.user
        if not user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url="/admin/login/")
        if not user.is_superuser:
            return HttpResponseForbidden("Platform owner only.")
        return view(request, *args, **kwargs)

    return wrapper


def _filtered_schools(request):
    qs = School.objects.annotate(
        student_count=Count("academics_student_set", distinct=True)
    ).prefetch_related(
        Prefetch("users", queryset=User.objects.filter(role="admin").order_by("id"), to_attr="admins")
    )

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")

    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(subdomain__icontains=q) | Q(eiin__icontains=q)
            | Q(email__icontains=q) | Q(phone__icontains=q) | Q(address__icontains=q)
        )
    if status == "active":
        qs = qs.filter(is_active=True)
    elif status == "suspended":
        qs = qs.filter(is_active=False)

    return qs.order_by("-created_at"), q, status


@owner_required
def owner_dashboard(request):
    qs, q, status = _filtered_schools(request)

    now = timezone.now()
    total = School.objects.count()
    active = School.objects.filter(is_active=True).count()
    payments = Payment.objects.aggregate(total=Sum("amount"), n=Count("id"))

    page_obj = Paginator(qs, 50).get_page(request.GET.get("page"))
    for s in page_obj.object_list:
        s.login_url = school_url(request, s.subdomain, "/login/")

    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "tenants/owner.html", {
        "page_obj": page_obj,
        "q": q, "status": status,
        "querystring": params.urlencode(),
        "current_url": request.get_full_path(),
        "stats": {
            "total": total,
            "active": active,
            "suspended": total - active,
            "new_7d": School.objects.filter(created_at__gte=now - timedelta(days=7)).count(),
            "new_30d": School.objects.filter(created_at__gte=now - timedelta(days=30)).count(),
            "students": Student.objects.count(),
            "payments_total": payments["total"] or 0,
            "payments_count": payments["n"],
        },
    })


@owner_required
def owner_export(request):
    qs, _, _ = _filtered_schools(request)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="schools.csv"'
    response.write("\ufeff")  # Excel reads Bangla correctly

    writer = csv.writer(response)
    writer.writerow([
        "School", "Subdomain", "EIIN", "Address", "Phone", "Email",
        "Admin username", "Students", "Status", "Registered",
    ])
    for s in qs:
        admin = s.admins[0].username if s.admins else ""
        writer.writerow([
            s.name, s.subdomain, s.eiin, s.address, s.phone, s.email, admin,
            s.student_count, "Active" if s.is_active else "Suspended",
            timezone.localtime(s.created_at).strftime("%Y-%m-%d %H:%M"),
        ])
    return response


@owner_required
@require_POST
def owner_toggle(request, pk):
    school = get_object_or_404(School, pk=pk)
    school.is_active = not school.is_active
    school.save(update_fields=["is_active"])
    if school.is_active:
        messages.success(request, f"{school.name} is active again.")
    else:
        messages.warning(request, f"{school.name} is suspended. Nobody from that school can log in.")

    # Go back to the same filtered page, but only to a safe address on this site.
    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("tenants:owner")
