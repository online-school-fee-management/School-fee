from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST


def role_home(user):
    """Where each role lands after login."""
    if user.role == "student":
        return "portal:home"
    if user.role in ("admin", "accountant", "teacher"):
        return "dashboard:home"
    return "/admin/"  # platform superuser


def home(request):
    # Main domain (no school subdomain) = public landing + school signup.
    if getattr(request, "school", None) is None:
        return render(request, "tenants/landing.html")

    if request.user.is_authenticated:
        return redirect(role_home(request.user))
    return redirect("accounts:login")


def login_view(request):
    school = getattr(request, "school", None)
    error = None

    if request.user.is_authenticated and school is not None:
        return redirect(role_home(request.user))

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.POST.get("next", "")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}
            ):
                return redirect(next_url)
            return redirect(role_home(user))
        error = "Invalid username or password."

    return render(request, "accounts/login.html", {
        "school": school,
        "error": error,
        "next": request.GET.get("next", ""),
    })


@require_POST
def logout_view(request):
    logout(request)
    return redirect("accounts:login")
