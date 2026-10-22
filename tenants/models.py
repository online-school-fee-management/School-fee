from django.db import models


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

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.subdomain})"


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
