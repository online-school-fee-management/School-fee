from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from academics.models import AcademicYear, SchoolClass

from .models import School

User = get_user_model()

DEFAULT_CLASS_COUNT = 10  # Class 1 ... Class 10


@transaction.atomic
def create_school(*, name, subdomain, eiin, address, phone, email,
                  admin_name, admin_username, admin_password, seed_defaults=True):
    """
    Everything a new school needs to start working immediately:
      - the School (tenant) itself, active right away
      - its first admin user
      - optionally the current academic year and Class 1-10
    Runs in one transaction: either everything is created or nothing is.
    """
    school = School.objects.create(
        name=name, subdomain=subdomain, eiin=eiin,
        address=address, phone=phone, email=email,
    )

    admin = User(
        school=school, username=admin_username, role="admin",
        first_name=admin_name[:150], email=email,
    )
    admin.set_password(admin_password)
    admin.save()

    if seed_defaults:
        today = timezone.localdate()
        AcademicYear.objects.create(
            school=school, name=str(today.year), is_current=True,
            start_date=today.replace(month=1, day=1),
            end_date=today.replace(month=12, day=31),
        )
        SchoolClass.objects.bulk_create([
            SchoolClass(school=school, name=f"Class {i}", order=i)
            for i in range(1, DEFAULT_CLASS_COUNT + 1)
        ])

    return school, admin
