from django import forms
from django.utils import timezone

from .models import AccountingSettings, CashTransaction
from .services import get_settings


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"


class AccountingSetupForm(BootstrapModelForm):
    class Meta:
        model = AccountingSettings
        fields = [
            "opening_cash",
            "opening_bank",
            "opening_date",
            "bank_name",
            "bank_account_number",
        ]
        widgets = {
            "opening_date": forms.DateInput(attrs={"type": "date"}),
            "opening_cash": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
            "opening_bank": forms.NumberInput(attrs={"min": "0", "step": "0.01"}),
        }

    def __init__(self, *args, school, **kwargs):
        self.school = school
        super().__init__(*args, **kwargs)

    def clean_opening_date(self):
        opening_date = self.cleaned_data["opening_date"]
        if opening_date > timezone.localdate():
            raise forms.ValidationError("The cash book cannot start in the future.")
        if self.instance.pk:
            earliest = (
                CashTransaction.objects.filter(
                    school=self.school, is_voided=False
                )
                .order_by("entry_date")
                .values_list("entry_date", flat=True)
                .first()
            )
            if earliest and opening_date > earliest:
                raise forms.ValidationError(
                    f"There is a transaction on {earliest:%d %b %Y}. "
                    "The cash book start date cannot be later than existing transactions."
                )
        return opening_date


class CashTransactionForm(BootstrapModelForm):
    class Meta:
        model = CashTransaction
        fields = [
            "transaction_type",
            "entry_date",
            "account_type",
            "category",
            "party",
            "amount",
            "reference",
            "description",
        ]
        widgets = {
            "entry_date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "transaction_type": forms.RadioSelect(),
        }
        labels = {
            "entry_date": "Date money moved",
            "account_type": "Money account",
            "category": "What was it for?",
            "party": "Received from / paid to",
            "reference": "Reference or slip number",
            "description": "Description",
        }

    def __init__(self, *args, school, **kwargs):
        self.school = school
        super().__init__(*args, **kwargs)
        self.fields["party"].widget.attrs["placeholder"] = (
            "Example: Rahim Uddin, City Bank, school supplier"
        )
        self.fields["reference"].required = False
        self.fields["description"].required = False
        self.fields["amount"].widget.attrs["placeholder"] = "0.00"
        if self.instance.pk:
            self.fields["transaction_type"].disabled = True

    def clean_entry_date(self):
        entry_date = self.cleaned_data["entry_date"]
        if entry_date > timezone.localdate():
            raise forms.ValidationError(
                "Enter today or an earlier date. Record money only after it has actually moved."
            )
        settings_obj = get_settings(self.school)
        if entry_date < settings_obj.opening_date:
            raise forms.ValidationError(
                f"The cash book starts on {settings_obj.opening_date:%d %b %Y}. "
                "Choose a date on or after that date, or change the start date in Setup."
            )
        return entry_date
