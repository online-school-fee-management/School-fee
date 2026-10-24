from django.test import TestCase, override_settings

from academics.models import AcademicYear, SchoolClass, Student
from accounts.models import User
from fees.models import FeeStructure, StudentFee
from tenants.models import School

from .models import Payment
from .receipts import verification_path


class ReceiptVerificationTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Receipt School",
            subdomain="receipt-school",
            phone="01700000000",
        )
        self.student_user = User.objects.create_user(
            username="student-1",
            password="test-password",
            school=self.school,
            role="student",
        )
        self.year = AcademicYear.objects.create(
            school=self.school,
            name="2026",
            is_current=True,
        )
        self.school_class = SchoolClass.objects.create(
            school=self.school,
            name="Class 8",
            section="A",
        )
        self.student = Student.objects.create(
            school=self.school,
            user=self.student_user,
            student_id="8001",
            name="Receipt Student",
            school_class=self.school_class,
            academic_year=self.year,
        )
        self.fee = StudentFee.objects.create(
            school=self.school,
            student=self.student,
            structure=FeeStructure.objects.create(
                school=self.school,
                fee_type="annual",
                title="Annual Fee",
                academic_year=self.year,
                school_class=self.school_class,
                amount=1200,
            ),
            amount=1200,
        )
        self.host = "receipt-school.localhost"

    @override_settings(ALLOW_TEST_PAYMENTS=True)
    def test_student_portal_payment_receipt_has_verification_qr(self):
        self.client.force_login(self.student_user)
        response = self.client.post(
            f"/portal/fees/{self.fee.pk}/pay/",
            {
                "gateway": "test",
                "amount": "1200.00",
            },
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Payment.objects.count(), 1)
        payment = Payment.objects.get()

        receipt_response = self.client.get(response.url, HTTP_HOST=self.host)
        self.assertEqual(receipt_response.status_code, 200)
        self.assertContains(receipt_response, "Online receipt verification")
        self.assertContains(receipt_response, "data:image/svg+xml;base64,")
        self.assertContains(receipt_response, payment.receipt_no)
        self.assertTrue(receipt_response.context["verification_url"])

        self.client.logout()
        verify_response = self.client.get(
            verification_path(payment),
            HTTP_HOST=self.host,
        )
        self.assertEqual(verify_response.status_code, 200)
        self.assertContains(verify_response, "This receipt is valid")
        self.assertContains(verify_response, "VERIFIED PAYMENT RECEIPT")
        self.assertContains(verify_response, payment.receipt_no)
        self.assertContains(verify_response, "Receipt Student")

    def test_verification_rejects_tampered_or_cross_school_links(self):
        payment = Payment.objects.create(
            school=self.school,
            student_fee=self.fee,
            amount=500,
            method=Payment.METHOD_CASH,
            receipt_no="R000001",
        )

        response = self.client.get(
            f"/receipts/verify/{payment.pk}/tampered-token/",
            HTTP_HOST=self.host,
        )
        self.assertEqual(response.status_code, 404)

        other_school = School.objects.create(
            name="Other School",
            subdomain="other-school",
        )
        response = self.client.get(
            verification_path(payment),
            HTTP_HOST=f"{other_school.subdomain}.localhost",
        )
        self.assertEqual(response.status_code, 404)
