from django.conf import settings
from django.core.validators import RegexValidator
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


class SchoolWebsite(models.Model):
    """Editable content for a school's public home page."""

    school = models.OneToOneField(
        School, on_delete=models.CASCADE, related_name="website"
    )
    logo = models.ImageField(
        upload_to="schools/website/", blank=True,
        help_text="Square or horizontal logo. PNG with transparency works best.",
    )
    hero_image = models.ImageField(
        upload_to="schools/website/", blank=True,
        help_text="Wide photo shown behind the welcome message.",
    )
    primary_color = models.CharField(
        max_length=7,
        default="#0d6b57",
        validators=[
            RegexValidator(
                regex=r"^#[0-9a-fA-F]{6}$",
                message="Enter a colour in the format #0d6b57.",
            )
        ],
    )
    hero_eyebrow = models.CharField(
        max_length=120, default="A community of curious minds"
    )
    hero_title = models.CharField(
        max_length=180, default="Learning today, leading tomorrow."
    )
    hero_subtitle = models.TextField(
        default=(
            "A caring school community where curiosity, character and confidence "
            "grow together."
        )
    )
    about_title = models.CharField(
        max_length=160, default="A place where every learner belongs"
    )
    about_text = models.TextField(
        default=(
            "Our teachers, families and staff work together to create a safe, "
            "welcoming environment where students are encouraged to ask questions, "
            "think independently and do their best."
        )
    )
    principal_name = models.CharField(max_length=150, blank=True)
    principal_title = models.CharField(
        max_length=120, default="Principal", blank=True
    )
    principal_message = models.TextField(blank=True)
    principal_photo = models.ImageField(
        upload_to="schools/website/", blank=True
    )
    admissions_open = models.BooleanField(
        default=True, verbose_name="Show admissions callout"
    )
    admissions_title = models.CharField(
        max_length=160, default="Admissions are open"
    )
    admissions_text = models.TextField(
        default=(
            "Visit the school office or contact us to learn about available classes, "
            "requirements and the next steps."
        )
    )
    footer_note = models.CharField(
        max_length=240,
        default="Learning with purpose, growing with confidence.",
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Website content - {self.school.name}"


class Notice(SchoolOwnedModel):
    title = models.CharField(max_length=180)
    content = models.TextField()
    published_on = models.DateField(default=timezone.localdate)
    is_important = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_important", "-published_on", "-created_at"]

    def __str__(self):
        return self.title


class GalleryImage(SchoolOwnedModel):
    title = models.CharField(max_length=160, blank=True)
    caption = models.CharField(max_length=240, blank=True)
    image = models.ImageField(upload_to="schools/gallery/")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "-created_at"]

    def __str__(self):
        return self.title or f"Gallery image {self.pk}"


class TeacherProfile(SchoolOwnedModel):
    name = models.CharField(max_length=150)
    designation = models.CharField(max_length=120)
    qualification = models.CharField(max_length=160, blank=True)
    bio = models.TextField(blank=True)
    photo = models.ImageField(upload_to="schools/teachers/", blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return f"{self.name} - {self.designation}"


class SubscriptionPayment(models.Model):
    """A school paying US for a plan (not to be confused with students paying the school)."""

    METHOD_DEMO = "demo"

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="subscription_payments")
    plan = models.CharField(max_length=20)
    months = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, default=METHOD_DEMO)
    reference = models.CharField(max_length=100, blank=True)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def invoice_no(self):
        return f"INV-{self.pk:06d}"

    @property
    def plan_label(self):
        return plans.get_plan(self.plan)["label"]

    def __str__(self):
        return f"{self.invoice_no} - {self.school.name} - {self.plan_label}"
