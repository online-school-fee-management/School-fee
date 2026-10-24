from django.contrib import admin

from .models import AccountingSettings, CashTransaction


@admin.register(AccountingSettings)
class AccountingSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "school",
        "opening_cash",
        "opening_bank",
        "opening_date",
        "bank_name",
    )
    search_fields = ("school__name", "school__subdomain", "bank_name")


@admin.register(CashTransaction)
class CashTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "voucher_no",
        "entry_date",
        "transaction_type",
        "account_type",
        "category",
        "party",
        "amount",
        "is_voided",
    )
    list_filter = (
        "transaction_type",
        "account_type",
        "category",
        "is_voided",
    )
    search_fields = (
        "voucher_no",
        "party",
        "reference",
        "description",
        "school__name",
    )
    readonly_fields = (
        "voucher_no",
        "source",
        "source_payment",
        "created_by",
        "created_at",
        "updated_at",
        "voided_at",
        "voided_by",
    )

    def has_add_permission(self, request):
        # Voucher numbers and cash-book validation come from the simple UI.
        return False
