from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden


def role_required(*roles):
    """
    Allow only logged-in users with one of the given roles,
    and only inside their own school's subdomain.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect_to_login(request.get_full_path())

            school = getattr(request, "school", None)
            if school is None or user.school_id != school.id:
                return HttpResponseForbidden("Access denied for this school.")

            if user.role not in roles:
                return HttpResponseForbidden("You do not have permission.")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
