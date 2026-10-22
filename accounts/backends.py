from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class SchoolBackend(ModelBackend):
    """
    Authenticate by (school, username, password).
    school comes from the subdomain (request.school); None = platform superusers.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        User = get_user_model()
        school = getattr(request, "school", None)
        user = User.objects.filter(username=username, school=school).first()

        if user is None:
            User().set_password(password)  # keep timing similar
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
