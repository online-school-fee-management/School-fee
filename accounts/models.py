from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    ROLE_ADMIN = "admin"
    ROLE_ACCOUNTANT = "accountant"
    ROLE_TEACHER = "teacher"
    ROLE_STUDENT = "student"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_ACCOUNTANT, "Accountant"),
        (ROLE_TEACHER, "Teacher"),
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
