from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from tenants.models import Notice, School, SchoolWebsite, TeacherProfile


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
            ("webmaster", "webmaster", "Website Manager"),
            ("auditor", "auditor", "Accounts Auditor"),
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

        website, website_created = SchoolWebsite.objects.get_or_create(school=school)
        if website_created:
            website.hero_eyebrow = "Welcome to Demo High School"
            website.hero_title = "Learning today, leading tomorrow."
            website.hero_subtitle = (
                "A caring school community where curiosity, character and "
                "confidence grow together."
            )
            website.about_title = "A place where every learner belongs"
            website.about_text = (
                "At Demo High School, our teachers and families work together "
                "to create a welcoming environment where every student is known, "
                "encouraged and challenged to do their best."
            )
            website.principal_name = "Nusrat Jahan"
            website.principal_title = "Principal"
            website.principal_message = (
                "We believe a strong school begins with care, curiosity and a "
                "genuine partnership between teachers, students and families."
            )
            website.save()

        today = timezone.localdate()
        notices = [
            (
                "Admission enquiries are now open",
                "Families interested in joining our school can visit the office "
                "or contact us to learn about available classes and admission steps.",
                today,
                True,
            ),
            (
                "Annual sports day",
                "Our annual sports day is coming soon. Students should watch the "
                "notice board for their event schedules and practice times.",
                today - timedelta(days=3),
                False,
            ),
            (
                "Parent-teacher meeting",
                "Guardians are invited to meet their child's class teacher and "
                "discuss progress, goals and ways to support learning at home.",
                today - timedelta(days=8),
                False,
            ),
        ]
        for title, content, published_on, important in notices:
            Notice.objects.get_or_create(
                school=school,
                title=title,
                defaults={
                    "content": content,
                    "published_on": published_on,
                    "is_important": important,
                },
            )

        teachers = [
            ("Nusrat Jahan", "Principal", "M.Ed, Education Leadership"),
            ("Arif Hossain", "Mathematics Teacher", "B.Sc in Mathematics"),
            ("Farhana Rahman", "English Teacher", "M.A. in English"),
            ("Tanvir Ahmed", "Science Teacher", "B.Sc in Physics"),
        ]
        for order, (name, designation, qualification) in enumerate(teachers):
            TeacherProfile.objects.get_or_create(
                school=school,
                name=name,
                defaults={
                    "designation": designation,
                    "qualification": qualification,
                    "display_order": order,
                },
            )

        self.stdout.write(self.style.SUCCESS(
            "Done. Open http://demo.localhost:8000/  (school website)\n"
            "Login at http://demo.localhost:8000/login/  (password: demo1234)"
        ))
