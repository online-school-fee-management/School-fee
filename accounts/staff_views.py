import secrets

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from tenants import plans

User = get_user_model()

STAFF_ROLES = ("admin", "accountant", "teacher")
ROLE_CHOICES = [
    ("admin", "Admin (full access)"),
    ("accountant", "Accountant (fees, payments and accounts)"),
    ("teacher", "Teacher (view students)"),
]
# no look-alike characters (0/O, 1/l/I) so a password can be read out or copied by hand
PASSWORD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"


def _generate_password(length=10):
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(length))


def _staff_qs(school):
    return User.objects.filter(school=school, role__in=STAFF_ROLES)


def _staff_quota(school):
    """(limit, active staff now). limit None = unlimited."""
    limit = plans.get_plan(school.effective_plan).get("staff_limit")
    used = _staff_qs(school).filter(is_active=True).count()
    return limit, used


def _limit_message(school, limit):
    return (
        f"Your {school.effective_plan_label} plan allows up to {limit} active staff accounts. "
        "Deactivate someone or contact us to upgrade your plan."
    )


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

@role_required("admin")
def staff_list(request):
    school = request.school
    limit, used = _staff_quota(school)
    return render(request, "staff/list.html", {
        "staff": _staff_qs(school).order_by("role", "first_name", "username"),
        "limit": limit,
        "used": used,
        "at_limit": limit is not None and used >= limit,
    })


# ---------------------------------------------------------------------------
# Add
# ---------------------------------------------------------------------------

@role_required("admin")
def staff_add(request):
    school = request.school
    limit, used = _staff_quota(school)

    if limit is not None and used >= limit:
        messages.error(request, _limit_message(school, limit))
        return redirect("staff:list")

    errors = []
    form = {"role": "accountant"}

    if request.method == "POST":
        form = request.POST
        name = request.POST.get("name", "").strip()
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        role = request.POST.get("role", "")
        password = request.POST.get("password", "")

        if not name:
            errors.append("Enter the person's full name.")

        try:
            if len(username) < 3 or len(username) > 50:
                raise ValidationError("length")
            User.username_validator(username)
        except ValidationError:
            errors.append("Username must be 3-50 characters (letters, numbers and @ . + - _ only).")
        else:
            if User.objects.filter(school=school, username__iexact=username).exists():
                errors.append(f"The username '{username}' is already taken.")

        if email:
            try:
                validate_email(email)
            except ValidationError:
                errors.append("Enter a valid email address or leave it empty.")

        if role not in STAFF_ROLES:
            errors.append("Please choose a role.")

        if password:
            if len(password) < 8:
                errors.append("Password must be at least 8 characters (or leave it empty to generate one).")
            elif password.lower() == username.lower():
                errors.append("Password cannot be the same as the username.")

        if not errors:
            generated = not password
            if generated:
                password = _generate_password()

            user = User(
                school=school, username=username, role=role,
                first_name=name[:150], email=email,
            )
            user.set_password(password)
            user.save()

            msg = f"{name} added as {user.get_role_display()}. Username: {username}."
            if generated:
                msg += f" Password: {password} (shown only now, please note it down)."
            messages.success(request, msg)
            return redirect("staff:list")

    return render(request, "staff/form.html", {
        "form": form, "errors": errors, "role_choices": ROLE_CHOICES,
        "target": None, "limit": limit, "used": used,
    })


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------

@role_required("admin")
def staff_edit(request, pk):
    school = request.school
    target = get_object_or_404(_staff_qs(school), pk=pk)
    is_self = target.pk == request.user.pk
    errors = []

    if request.method == "POST":
        form = request.POST
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()

        # You cannot demote or deactivate yourself (that could lock the school out).
        if is_self:
            role = target.role
            is_active = True
        else:
            role = request.POST.get("role", "")
            is_active = request.POST.get("is_active") == "on"

        if not name:
            errors.append("Enter the person's full name.")
        if email:
            try:
                validate_email(email)
            except ValidationError:
                errors.append("Enter a valid email address or leave it empty.")
        if role not in STAFF_ROLES:
            errors.append("Please choose a role.")

        # Switching an inactive account back on needs a free staff slot.
        if not errors and is_active and not target.is_active:
            limit, used = _staff_quota(school)
            if limit is not None and used >= limit:
                errors.append(_limit_message(school, limit))

        if not errors:
            target.first_name = name[:150]
            target.email = email
            target.role = role
            target.is_active = is_active
            target.save(update_fields=["first_name", "email", "role", "is_active"])
            messages.success(request, f"{name} updated.")
            return redirect("staff:list")
    else:
        form = {
            "name": target.first_name, "username": target.username, "email": target.email,
            "role": target.role, "is_active": "on" if target.is_active else "",
        }

    return render(request, "staff/form.html", {
        "form": form, "errors": errors, "role_choices": ROLE_CHOICES,
        "target": target, "is_self": is_self,
    })


# ---------------------------------------------------------------------------
# Reset password
# ---------------------------------------------------------------------------

@role_required("admin")
@require_POST
def staff_reset_password(request, pk):
    target = get_object_or_404(_staff_qs(request.school), pk=pk)

    if target.pk == request.user.pk:
        messages.error(request, "Use \"Change password\" in the top bar to change your own password.")
        return redirect("staff:list")

    password = _generate_password()
    target.set_password(password)
    target.save(update_fields=["password"])
    messages.success(
        request,
        f"New password for {target.username}: {password} (shown only now, please note it down).",
    )
    return redirect("staff:list")
