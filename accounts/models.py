from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    ROLE_ADMIN = "admin"
    ROLE_ACCOUNTANT = "accountant"
    ROLE_TEACHER = "teacher"
    ROLE_WEBMASTER = "webmaster"
    ROLE_AUDITOR = "auditor"
    ROLE_STUDENT = "student"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_ACCOUNTANT, "Accountant"),
        (ROLE_TEACHER, "Teacher"),
        (ROLE_WEBMASTER, "Webmaster"),
        (ROLE_AUDITOR, "Auditor"),
        (ROLE_STUDENT, "Student"),
    ]

    # Username is unique PER SCHOOL (two schools can both have student "1001").
    # Platform superusers have school = NULL and a globally unique username.
    username = models.CharField(
        max_length=150, validators=[AbstractUser.username_validator]
    )
    school = models.ForeignKey(
        "tenants.School",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["school", "username"], name="uniq_school_username"
            ),
            models.UniqueConstraint(
                fields=["username"],
                condition=Q(school__isnull=True),
                name="uniq_platform_username",
            ),
        ]

    def __str__(self):
        return f"{self.username} ({self.role or 'superuser'})"

    @property
    def can_manage_fees(self):
        return self.role in (
            self.ROLE_ADMIN, self.ROLE_ACCOUNTANT, self.ROLE_TEACHER,
        )

    @property
    def can_view_students(self):
        return self.can_manage_fees

    @property
    def can_view_fees(self):
        return self.can_manage_fees or self.role == self.ROLE_AUDITOR

    @property
    def can_manage_accounts(self):
        return self.role in (self.ROLE_ADMIN, self.ROLE_ACCOUNTANT)

    @property
    def can_view_accounts(self):
        return self.can_manage_accounts or self.role == self.ROLE_AUDITOR

    @property
    def can_manage_website(self):
        return self.role in (self.ROLE_ADMIN, self.ROLE_WEBMASTER)
