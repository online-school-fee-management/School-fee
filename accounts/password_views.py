from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from .views import role_home


def change_password(request):
    """Any logged-in person of a school (staff or student) can change their own password."""
    user = request.user
    if not user.is_authenticated:
        return redirect_to_login(request.get_full_path())

    school = getattr(request, "school", None)
    if school is None or user.school_id != school.id:
        return HttpResponseForbidden("Access denied for this school.")

    errors = []
    if request.method == "POST":
        current = request.POST.get("current_password", "")
        new = request.POST.get("new_password", "")
        confirm = request.POST.get("confirm_password", "")

        if not user.check_password(current):
            errors.append("Your current password is not correct.")
        elif len(new) < 8:
            errors.append("The new password must be at least 8 characters.")
        elif new == current:
            errors.append("The new password must be different from the current one.")
        elif new.lower() == user.username.lower():
            errors.append("The new password cannot be the same as your username.")
        elif new != confirm:
            errors.append("The two new passwords do not match.")

        if not errors:
            user.set_password(new)
            user.save(update_fields=["password"])
            update_session_auth_hash(request, user)  # keep this person logged in
            messages.success(request, "Your password has been changed.")
            return redirect(role_home(user))

    return render(request, "accounts/change_password.html", {"errors": errors})
