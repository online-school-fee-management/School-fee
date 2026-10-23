from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property

from . import plans


class School(models.Model):
    """One school = one tenant. Identified by subdomain."""

    name = models.CharField(max_length=200)
    subdomain = models.SlugField(max_length=63, unique=True)
    eiin = models.CharField("EIIN", max_length=20, blank=True)
    address = models.CharField(max_length=300, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Plan: a key from tenants/plans.py (trial, free, basic, standard, premium).
    # plan_expires_at empty = never expires.
    plan = models.CharField(max_length=20, default="trial")
    plan_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.subdomain})"

    # ---- plan helpers ------------------------------------------------------

    @property
    def effective_plan(self):
        """The plan the school really has today (an expired plan counts as free)."""
        if self.plan != "free" and self.plan_expires_at and timezone.now() > self.plan_expires_at:
            return "free"
        return self.plan

    @property
    def is_plan_expired(self):
        return self.effective_plan == "free" and self.plan != "free"

    @property
    def plan_label(self):
        """Label of the plan that was assigned (even if it has expired)."""
        return plans.get_plan(self.plan)["label"]

    @property
    def effective_plan_label(self):
        return plans.get_plan(self.effective_plan)["label"]

    @property
    def student_limit(self):
        """None = unlimited."""
        return plans.get_plan(self.effective_plan).get("student_limit")

    def allows(self, feature):
        return bool(plans.get_plan(self.effective_plan).get(feature))

    def students_used(self):
        return self.academics_student_set.count()

    def students_remaining(self):
        """None = unlimited."""
        limit = self.student_limit
        if limit is None:
            return None
        return max(limit - self.students_used(), 0)

    def can_add_students(self, count=1):
        remaining = self.students_remaining()
        return remaining is None or remaining >= count

    @cached_property
    def plan_info(self):
        """Everything the dashboard banner needs (computed once per request)."""
        limit = self.student_limit
        used = self.students_used()
        days_left = None
        if self.effective_plan != "free" and self.plan_expires_at:
            days_left = max((self.plan_expires_at - timezone.now()).days, 0)
        return {
            "key": self.effective_plan,
            "label": self.effective_plan_label,
            "limit": limit,
            "used": used,
            "percent": min(int(used * 100 / limit), 100) if limit else None,
            "days_left": days_left,
            "expired": self.is_plan_expired,
            "at_limit": limit is not None and used >= limit,
            "near_limit": bool(limit) and used < limit and used * 100 >= limit * 90,
        }


class SchoolOwnedModel(models.Model):
    """
    Base class for every tenant-specific table (classes, students, fees...).
    Always filter with: Model.objects.filter(school=request.school)
    """

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
    )

    class Meta:
        abstract = True
