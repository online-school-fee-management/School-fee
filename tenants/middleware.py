from django.http import HttpResponse

from django.conf import settings

from .models import School


class TenantMiddleware:
    """
    Sets request.school from the subdomain.
      abc.localhost:8000  -> School(subdomain="abc")
      localhost:8000      -> request.school = None (platform level, e.g. /admin/)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0].lower()
        base = settings.BASE_DOMAIN.lower()

        subdomain = None
        if host.endswith("." + base):
            subdomain = host[: -(len(base) + 1)]
            if subdomain in ("", "www"):
                subdomain = None

        school = None
        if subdomain:
            school = School.objects.filter(subdomain=subdomain, is_active=True).first()
            if school is None:
                return HttpResponse("School not found or inactive.", status=404)

        request.school = school
        return self.get_response(request)
