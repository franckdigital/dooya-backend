from django.contrib import admin
from .models import CommissionRule, Commission, VendorPayout


@admin.register(CommissionRule)
class CommissionRuleAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'store', 'category', 'rate', 'flat_fee', 'is_active']
    list_filter = ['is_active']
    search_fields = ['store__name', 'category__name']


class CommissionInline(admin.TabularInline):
    model = Commission
    extra = 0
    readonly_fields = ['order', 'store', 'order_amount', 'rate_applied', 'commission_amount',
                       'vendor_amount', 'status', 'paid_at']
    can_delete = False
    max_num = 0


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ['order', 'store', 'order_amount', 'commission_amount', 'vendor_amount',
                    'status', 'paid_at', 'created_at']
    list_filter = ['status', 'store']
    search_fields = ['order__order_number', 'store__name']
    readonly_fields = ['order', 'store', 'rule', 'order_amount', 'rate_applied',
                       'flat_fee_applied', 'commission_amount', 'vendor_amount', 'paid_at']
    ordering = ['-created_at']


@admin.register(VendorPayout)
class VendorPayoutAdmin(admin.ModelAdmin):
    list_display = ['reference', 'store', 'total_payout', 'status', 'method', 'period_start', 'period_end', 'processed_at']
    list_filter = ['status', 'method', 'store']
    search_fields = ['reference', 'store__name']
    readonly_fields = ['reference', 'total_order_amount', 'total_commission', 'total_payout', 'created_at']
    inlines = [CommissionInline]
    ordering = ['-created_at']
    actions = ['mark_paid']

    def mark_paid(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status__in=['pending', 'processing']).update(
            status='paid',
            processed_by=request.user,
            processed_at=timezone.now(),
        )
        self.message_user(request, f'{updated} reversement(s) marqué(s) comme payé(s).')
    mark_paid.short_description = 'Marquer comme payés'
