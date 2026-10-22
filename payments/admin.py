from django.contrib import admin

from .models import Payment, ReceiptSequence


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("receipt_no", "student_fee", "amount", "method", "paid_at", "school")
    list_filter = ("school", "method")
    search_fields = ("receipt_no", "reference", "student_fee__student__student_id")


admin.site.register(ReceiptSequence)
