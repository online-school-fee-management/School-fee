from django.test import TestCase

from accounts.models import User

from .models import Notice, School


class SchoolWebsiteTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Green Valley School",
            subdomain="green-valley",
            phone="01700000000",
            email="office@example.com",
            address="12 School Road",
        )
        self.admin = User.objects.create_user(
            username="admin",
            password="test-password",
            school=self.school,
            role="admin",
            first_name="School Admin",
        )
        self.teacher = User.objects.create_user(
            username="teacher",
            password="test-password",
            school=self.school,
            role="teacher",
        )
        self.host = "green-valley.localhost"

    def test_tenant_root_shows_public_school_website(self):
        response = self.client.get("/", HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Green Valley School")
        self.assertContains(response, "Learning today, leading tomorrow.")
        self.assertContains(response, "From the notice board")
        self.assertContains(response, "Portal Login")

    def test_login_page_remains_available(self):
        response = self.client.get("/login/", HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")
        self.assertContains(response, "Green Valley School")

    def test_signed_in_admin_can_preview_public_site(self):
        self.client.force_login(self.admin)
        response = self.client.get("/", HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "School Dashboard")
        self.assertContains(response, "From the notice board")

    def test_school_admin_can_open_website_editor(self):
        self.client.force_login(self.admin)

        for path in (
            "/dashboard/website/",
            "/dashboard/website/settings/",
            "/dashboard/website/notices/",
            "/dashboard/website/gallery/",
            "/dashboard/website/teachers/",
        ):
            with self.subTest(path=path):
                response = self.client.get(path, HTTP_HOST=self.host)
                self.assertEqual(response.status_code, 200)

    def test_non_admin_cannot_open_website_editor(self):
        self.client.force_login(self.teacher)
        response = self.client.get(
            "/dashboard/website/settings/", HTTP_HOST=self.host
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_updates_content_and_notice_appears_publicly(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            "/dashboard/website/settings/",
            {
                "form_kind": "website",
                "primary_color": "#145c4c",
                "hero_eyebrow": "Our school",
                "hero_title": "A brighter start",
                "hero_subtitle": "Learning together every day.",
                "about_title": "Welcome to Green Valley",
                "about_text": "A supportive learning community.",
                "principal_name": "A. Principal",
                "principal_title": "Principal",
                "principal_message": "Welcome to our school.",
                "admissions_open": "on",
                "admissions_title": "Join our school",
                "admissions_text": "Contact the office for admission details.",
                "footer_note": "Learn and grow together.",
            },
            HTTP_HOST=self.host,
        )
        self.assertRedirects(
            response,
            "/dashboard/website/settings/",
            fetch_redirect_response=False,
        )

        response = self.client.post(
            "/dashboard/website/notices/add/",
            {
                "title": "Annual sports day",
                "content": "The sports day will be held next Friday.",
                "published_on": "2026-10-23",
                "is_important": "on",
                "is_active": "on",
            },
            HTTP_HOST=self.host,
        )
        self.assertRedirects(
            response,
            "/dashboard/website/notices/",
            fetch_redirect_response=False,
        )
        self.assertTrue(
            Notice.objects.filter(
                school=self.school, title="Annual sports day"
            ).exists()
        )

        self.client.logout()
        response = self.client.get("/", HTTP_HOST=self.host)
        self.assertContains(response, "A brighter start")
        self.assertContains(response, "Annual sports day")
