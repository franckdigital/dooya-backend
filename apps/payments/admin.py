from django.contrib import admin
from .models import Payment, Refund, InstallmentPlan, Installment


class InstallmentInline(admin.TabularInline):
    model = Installment
    extra = 0
    readonly_fields = ['amount', 'due_date', 'paid_at', 'status']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['reference', 'order', 'amount', 'currency', 'method', 'gateway', 'status', 'paid_at', 'created_at']
    list_filter = ['status', 'gateway', 'method', 'currency']
    search_fields = ['reference', 'transaction_id', 'order__order_number']
    readonly_fields = ['reference', 'transaction_id', 'paid_at', 'created_at']


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['payment', 'amount', 'status', 'processed_at', 'created_at']
    list_filter = ['status']
    search_fields = ['payment__reference']


@admin.register(InstallmentPlan)
class InstallmentPlanAdmin(admin.ModelAdmin):
    list_display = ['order', 'total_amount', 'installments_count', 'frequency', 'status']
    list_filter = ['status', 'frequency']
    inlines = [InstallmentInline]
