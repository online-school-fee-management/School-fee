from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from tenants.models import School


class Command(BaseCommand):
    help = "Create a demo school (subdomain 'demo') with one user per role."

    def handle(self, *args, **options):
        User = get_user_model()

        school, _ = School.objects.get_or_create(
            subdomain="demo",
            defaults={"name": "Demo High School", "eiin": "000000"},
        )

        users = [
            ("admin", "admin", "School Admin"),
            ("accountant", "accountant", "School Accountant"),
            ("teacher", "teacher", "Class Teacher"),
            ("student", "student", "Demo Student"),
        ]
        for username, role, full_name in users:
            user, created = User.objects.get_or_create(
                school=school, username=username,
                defaults={"role": role, "first_name": full_name},
            )
            user.role = role
            user.set_password("demo1234")
            user.save()
            state = "created" if created else "updated"
            self.stdout.write(f"  {username} ({role}) {state}")

        self.stdout.write(self.style.SUCCESS(
            "Done. Open http://demo.localhost:8000/login/  (password: demo1234)"
        ))
