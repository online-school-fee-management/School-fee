import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .models import School
from .services import create_school

User = get_user_model()

SUBDOMAIN_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,28}[a-z0-9]$")  # 3-30 chars
PHONE_RE = re.compile(r"^[0-9+\-\s()]{6,20}$")
EIIN_RE = re.compile(r"^\d{4,10}$")

# Addresses nobody may register (they would clash with our own pages/services).
RESERVED_SUBDOMAINS = {
    "www", "admin", "api", "app", "mail", "email", "ftp", "static", "media",
    "support", "help", "billing", "dashboard", "portal", "login", "logout",
    "signup", "register", "account", "accounts", "owner", "root", "system",
    "test", "staging", "dev", "docs", "blog", "status", "cdn", "assets",
}

MAX_SIGNUPS_PER_HOUR = 5  # per IP address


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _base_host(request):
    """'localhost:8000' (keeps the port while developing)."""
    host = request.get_host()
    port = host.split(":", 1)[1] if ":" in host else ""
    return settings.BASE_DOMAIN + (f":{port}" if port else "")


def school_url(request, subdomain, path="/"):
    return f"{request.scheme}://{subdomain}.{_base_host(request)}{path}"


def _client_ip(request):
    # Behind a proxy/load balancer, configure it so REMOTE_ADDR is the real client.
    return request.META.get("REMOTE_ADDR", "unknown")


def subdomain_error(value):
    """Returns a message if the address cannot be used, else None."""
    if not SUBDOMAIN_RE.match(value) or "--" in value:
        return "Address must be 3-30 characters: lowercase letters, numbers and single hyphens (not at the start or end)."
    if value in RESERVED_SUBDOMAINS:
        return "This address is reserved. Please choose another."
    if School.objects.filter(subdomain=value).exists():
        return "This address is already taken."
    return None


# ---------------------------------------------------------------------------
# views (all on the main domain, no school subdomain)
# ---------------------------------------------------------------------------

def check_subdomain(request):
    """Used by the signup page to show 'available / taken' while typing."""
    value = request.GET.get("name", "").strip().lower()
    error = subdomain_error(value) if value else "Enter an address."
    return JsonResponse({"ok": error is None, "message": error or "Available"})


def find_school(request):
    """Landing page box: 'I already registered' -> go to my school's login."""
    if request.method != "POST":
        return redirect("accounts:home")

    value = request.POST.get("subdomain", "").strip().lower()
    school = School.objects.filter(subdomain=value, is_active=True).first() if value else None
    if school:
        return redirect(school_url(request, school.subdomain, "/login/"))

    return render(request, "tenants/landing.html", {
        "find_error": "No school found with that address.",
        "find_value": value,
    })


def signup(request):
    if getattr(request, "school", None) is not None:
        return redirect("accounts:home")  # signup only exists on the main domain

    errors = []
    form = {"admin_username": "admin", "seed_defaults": "on"}

    if request.method == "POST":
        form = request.POST
        ip = _client_ip(request)
        rate_key = f"signup-count:{ip}"

        if request.POST.get("website"):  # honeypot: real people never fill this hidden field
            errors.append("Could not submit the form. Please try again.")
        elif cache.get(rate_key, 0) >= MAX_SIGNUPS_PER_HOUR:
            errors.append("Too many registrations from your network. Please try again later.")
        else:
            p = request.POST
            name = p.get("school_name", "").strip()
            subdomain = p.get("subdomain", "").strip().lower()
            eiin = p.get("eiin", "").strip()
            address = p.get("address", "").strip()
            phone = p.get("phone", "").strip()
            email = p.get("email", "").strip()
            admin_name = p.get("admin_name", "").strip()
            username = p.get("admin_username", "").strip()
            password = p.get("password", "")
            password2 = p.get("password2", "")

            if len(name) < 3:
                errors.append("Enter the school name.")
            elif len(name) > 200:
                errors.append("School name is too long.")

            err = subdomain_error(subdomain)
            if err:
                errors.append(err)

            if eiin:
                if not EIIN_RE.match(eiin):
                    errors.append("EIIN must contain digits only.")
                elif School.objects.filter(eiin=eiin).exists():
                    errors.append("A school with this EIIN is already registered. Please contact support.")

            if not address:
                errors.append("Enter the school address.")
            if not PHONE_RE.match(phone):
                errors.append("Enter a valid contact phone number.")
            try:
                validate_email(email)
            except ValidationError:
                errors.append("Enter a valid email address.")

            if not admin_name:
                errors.append("Enter the name of the person who will manage the account.")
            try:
                if len(username) < 3 or len(username) > 50:
                    raise ValidationError("length")
                User.username_validator(username)
            except ValidationError:
                errors.append("Username must be 3-50 characters (letters, numbers and @ . + - _ only).")

            if len(password) < 8:
                errors.append("Password must be at least 8 characters.")
            elif password.lower() == username.lower():
                errors.append("Password cannot be the same as the username.")
            elif password != password2:
                errors.append("The two passwords do not match.")

            if p.get("agree") != "on":
                errors.append("Please confirm that you are authorized to register this school.")

            if not errors:
                try:
                    school, _ = create_school(
                        name=name, subdomain=subdomain, eiin=eiin, address=address,
                        phone=phone, email=email, admin_name=admin_name,
                        admin_username=username, admin_password=password,
                        seed_defaults=p.get("seed_defaults") == "on",
                    )
                except IntegrityError:
                    errors.append("That address was just taken. Please choose another.")
                else:
                    cache.set(rate_key, cache.get(rate_key, 0) + 1, 3600)
                    request.session["signup_info"] = {
                        "subdomain": school.subdomain, "username": username,
                        "seeded": p.get("seed_defaults") == "on",
                    }
                    return redirect("tenants:signup_done")

    return render(request, "tenants/signup.html", {
        "form": form, "errors": errors, "base_host": _base_host(request),
    })


def signup_done(request):
    info = request.session.get("signup_info")
    school = School.objects.filter(subdomain=info["subdomain"]).first() if info else None
    if not school:
        return redirect("tenants:signup")

    return render(request, "tenants/signup_done.html", {
        "school": school,
        "username": info["username"],
        "seeded": info.get("seeded"),
        "login_url": school_url(request, school.subdomain, "/login/"),
        "site_url": school_url(request, school.subdomain, "/"),
    })
