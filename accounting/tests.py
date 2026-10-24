import datetime
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from openpyxl import Workbook

from academics.models import AcademicYear, SchoolClass, Student
from accounts.models import User
from fees.models import FeeStructure, StudentFee
from payments.services import record_payment, void_payment
from tenants.models import School

from .models import CashTransaction
from .services import account_balance, get_settings


class AccountingTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name="Ledger School",
            subdomain="ledger-school",
        )
        self.admin = User.objects.create_user(
            username="admin",
            password="test-password",
            school=self.school,
            role="admin",
        )
        self.accountant = User.objects.create_user(
            username="accountant",
            password="test-password",
            school=self.school,
            role="accountant",
        )
        self.teacher = User.objects.create_user(
            username="teacher",
            password="test-password",
            school=self.school,
            role="teacher",
        )
        self.auditor = User.objects.create_user(
            username="auditor",
            password="test-password",
            school=self.school,
            role="auditor",
        )
        self.host = "ledger-school.localhost"
        self.ledger_settings = get_settings(self.school)
        self.ledger_settings.opening_cash = 2000
        self.ledger_settings.opening_bank = 4000
        self.ledger_settings.opening_date = timezone.localdate()
        self.ledger_settings.save()

    def _post_entry(self, **overrides):
        data = {
            "transaction_type": "receipt",
            "entry_date": timezone.localdate().isoformat(),
            "account_type": "cash",
            "category": "donation",
            "party": "Community donor",
            "amount": "1000.00",
            "reference": "DON-001",
            "description": "Library books",
        }
        data.update(overrides)
        return self.client.post(
            "/dashboard/accounting/entries/new/",
            data,
            HTTP_HOST=self.host,
        )

    def test_accountant_can_record_receipt_and_payment(self):
        self.client.force_login(self.accountant)
        response = self._post_entry()
        self.assertEqual(response.status_code, 302)
        receipt = CashTransaction.objects.get(transaction_type="receipt")
        self.assertEqual(receipt.voucher_no, "RV-000001")
        self.assertEqual(
            account_balance(self.school, CashTransaction.ACCOUNT_CASH),
            3000,
        )

        response = self._post_entry(
            transaction_type="payment",
            account_type="bank",
            category="utilities",
            party="Electricity supplier",
            amount="250.00",
            reference="BILL-10",
            description="Electricity bill",
        )
        self.assertEqual(response.status_code, 302)
        payment = CashTransaction.objects.get(transaction_type="payment")
        self.assertEqual(payment.voucher_no, "PV-000001")
        self.assertEqual(
            account_balance(self.school, CashTransaction.ACCOUNT_BANK),
            3750,
        )

        response = self.client.get(
            "/dashboard/accounting/ledger/?account=cash&date_from="
            f"{timezone.localdate().isoformat()}&date_to={timezone.localdate().isoformat()}",
            HTTP_HOST=self.host,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "3000.00")

    def test_teacher_cannot_open_accounting(self):
        self.client.force_login(self.teacher)
        response = self.client.get(
            "/dashboard/accounting/", HTTP_HOST=self.host
        )
        self.assertEqual(response.status_code, 403)

    def test_teacher_can_manage_fees_and_collect_payment(self):
        year = AcademicYear.objects.create(
            school=self.school,
            name="2026",
            is_current=True,
        )
        school_class = SchoolClass.objects.create(
            school=self.school,
            name="Class 7",
            section="A",
        )
        student = Student.objects.create(
            school=self.school,
            student_id="7001",
            name="Teacher Test Student",
            school_class=school_class,
            academic_year=year,
        )
        structure = FeeStructure.objects.create(
            school=self.school,
            fee_type="annual",
            title="Annual Fee",
            academic_year=year,
            school_class=school_class,
            amount=500,
        )
        fee = StudentFee.objects.create(
            school=self.school,
            student=student,
            structure=structure,
            amount=500,
        )
        self.client.force_login(self.teacher)

        self.assertEqual(
            self.client.get(
                "/dashboard/fees/", HTTP_HOST=self.host
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                "/dashboard/payments/", HTTP_HOST=self.host
            ).status_code,
            200,
        )

        response = self.client.post(
            f"/dashboard/payments/due/{fee.pk}/collect/",
            {
                "amount": "200.00",
                "method": "cash",
                "account_type": "cash",
                "reference": "",
                "note": "Collected by class teacher",
            },
            HTTP_HOST=self.host,
        )
        self.assertEqual(response.status_code, 302)
        fee.refresh_from_db()
        self.assertEqual(fee.paid_amount, 200)

    def test_auditor_can_view_export_and_download_but_not_change_accounts(self):
        self.client.force_login(self.admin)
        response = self._post_entry()
        self.assertEqual(response.status_code, 302)
        entry = CashTransaction.objects.get()

        self.client.force_login(self.auditor)
        for path in (
            "/dashboard/accounting/",
            "/dashboard/accounting/entries/",
            f"/dashboard/accounting/entries/{entry.pk}/",
            "/dashboard/accounting/ledger/",
            "/dashboard/accounting/export/?format=csv",
            "/dashboard/payments/",
        ):
            with self.subTest(path=path):
                response = self.client.get(path, HTTP_HOST=self.host)
                self.assertEqual(response.status_code, 200)

        response = self.client.get(
            f"/dashboard/accounting/entries/{entry.pk}/download/",
            HTTP_HOST=self.host,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

        for path in (
            "/dashboard/accounting/setup/",
            "/dashboard/accounting/entries/new/",
            "/dashboard/accounting/import/",
        ):
            with self.subTest(path=path):
                response = self.client.get(path, HTTP_HOST=self.host)
                self.assertEqual(response.status_code, 403)

        response = self.client.post(
            f"/dashboard/accounting/entries/{entry.pk}/void/",
            {"reason": "Auditor must not be able to void"},
            HTTP_HOST=self.host,
        )
        self.assertEqual(response.status_code, 403)
        entry.refresh_from_db()
        self.assertFalse(entry.is_voided)

    def test_future_dated_transaction_is_rejected(self):
        self.client.force_login(self.accountant)
        tomorrow = timezone.localdate() + datetime.timedelta(days=1)
        response = self._post_entry(entry_date=tomorrow.isoformat())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(CashTransaction.objects.count(), 0)
        self.assertContains(response, "Record money only after it has actually moved")

    def test_excel_import_creates_transactions(self):
        self.client.force_login(self.accountant)
        workbook = Workbook()
        sheet = workbook.active
        sheet.append([
            "Type",
            "Date",
            "Account",
            "Category",
            "Party",
            "Amount",
            "Reference",
            "Description",
        ])
        sheet.append([
            "Receipt",
            timezone.localdate(),
            "Cash",
            "Admission fees",
            "New student",
            1500,
            "ADM-1",
            "Admission collection",
        ])
        sheet.append([
            "Payment",
            timezone.localdate(),
            "Bank",
            "Supplies",
            "Stationery shop",
            500,
            "INV-2",
            "Printer paper",
        ])
        buffer = BytesIO()
        workbook.save(buffer)
        upload = SimpleUploadedFile(
            "transactions.xlsx",
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response = self.client.post(
            "/dashboard/accounting/import/",
            {"file": upload},
            HTTP_HOST=self.host,
        )
        self.assertRedirects(
            response,
            "/dashboard/accounting/entries/",
            fetch_redirect_response=False,
        )
        self.assertEqual(CashTransaction.objects.count(), 2)
        self.assertEqual(
            account_balance(self.school, CashTransaction.ACCOUNT_CASH),
            3500,
        )
        self.assertEqual(
            account_balance(self.school, CashTransaction.ACCOUNT_BANK),
            3500,
        )

        response = self.client.get(
            "/dashboard/accounting/export/", HTTP_HOST=self.host
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            response["Content-Type"],
        )

    def test_import_rejects_file_if_any_row_is_invalid(self):
        self.client.force_login(self.accountant)
        workbook = Workbook()
        sheet = workbook.active
        sheet.append([
            "Type",
            "Date",
            "Account",
            "Category",
            "Party",
            "Amount",
        ])
        sheet.append([
            "Receipt",
            timezone.localdate(),
            "Cash",
            "Donation",
            "Valid donor",
            100,
        ])
        sheet.append([
            "Payment",
            timezone.localdate(),
            "Bank",
            "Unknown category",
            "Supplier",
            50,
        ])
        buffer = BytesIO()
        workbook.save(buffer)
        upload = SimpleUploadedFile(
            "invalid.xlsx",
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response = self.client.post(
            "/dashboard/accounting/import/",
            {"file": upload},
            HTTP_HOST=self.host,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CashTransaction.objects.count(), 0)
        self.assertContains(response, "Nothing was imported")

    def test_student_fee_collection_posts_and_voids_receipt(self):
        year = AcademicYear.objects.create(
            school=self.school,
            name="2026",
            is_current=True,
        )
        school_class = SchoolClass.objects.create(
            school=self.school,
            name="Class 6",
            section="A",
        )
        student = Student.objects.create(
            school=self.school,
            student_id="6001",
            name="Rahim Uddin",
            school_class=school_class,
            academic_year=year,
        )
        structure = FeeStructure.objects.create(
            school=self.school,
            fee_type="annual",
            title="Annual Fee",
            academic_year=year,
            school_class=school_class,
            amount=500,
        )
        fee = StudentFee.objects.create(
            school=self.school,
            student=student,
            structure=structure,
            amount=500,
        )
        payment = record_payment(
            school=self.school,
            fee_id=fee.pk,
            amount=500,
            method="cash",
            reference="",
            note="",
            user=self.accountant,
        )
        receipt = payment.accounting_entry
        self.assertEqual(receipt.transaction_type, "receipt")
        self.assertEqual(receipt.account_type, "cash")
        self.assertEqual(receipt.party, "Rahim Uddin")
        self.assertEqual(receipt.category, "student_fees")
        self.assertEqual(
            account_balance(self.school, CashTransaction.ACCOUNT_CASH),
            2500,
        )

        payment_id = payment.pk
        void_payment(payment)
        self.assertFalse(
            CashTransaction.objects.filter(source_payment_id=payment_id).exists()
        )
        self.assertEqual(
            account_balance(self.school, CashTransaction.ACCOUNT_CASH),
            2000,
        )
