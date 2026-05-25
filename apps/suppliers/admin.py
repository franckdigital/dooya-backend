from django.contrib import admin
from .models import Supplier, SupplierProduct, SupplierContract, SupplierPerformanceReport


class SupplierProductInline(admin.TabularInline):
    model = SupplierProduct
    extra = 0
    raw_id_fields = ['product', 'variant']
    fields = ['product', 'variant', 'supplier_sku', 'unit_cost', 'min_order_quantity', 'is_preferred']


class SupplierContractInline(admin.TabularInline):
    model = SupplierContract
    extra = 0
    fields = ['reference', 'status', 'start_date', 'end_date']
    readonly_fields = ['reference']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'country', 'quality_rating', 'quality_score',
        'defect_rate', 'is_approved', 'is_active',
    ]
    list_filter = ['quality_rating', 'is_approved', 'is_active', 'country']
    search_fields = ['name', 'code', 'email']
    readonly_fields = ['quality_score', 'defect_rate', 'on_time_delivery_rate', 'created_at', 'updated_at']
    inlines = [SupplierProductInline, SupplierContractInline]
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'code', 'contact_name', 'email', 'phone', 'whatsapp',
                       'address', 'city', 'country', 'website')
        }),
        ('Conditions commerciales', {
            'fields': ('payment_terms', 'lead_time_days', 'currency', 'min_order_amount')
        }),
        ('Qualité', {
            'fields': ('quality_rating', 'quality_score', 'defect_rate', 'on_time_delivery_rate')
        }),
        ('Statut', {
            'fields': ('is_active', 'is_approved', 'managed_by', 'notes')
        }),
    )


@admin.register(SupplierContract)
class SupplierContractAdmin(admin.ModelAdmin):
    list_display = ['reference', 'supplier', 'status', 'start_date', 'end_date', 'is_active']
    list_filter = ['status']
    search_fields = ['reference', 'supplier__name']
    readonly_fields = ['reference', 'created_at']


@admin.register(SupplierPerformanceReport)
class SupplierPerformanceAdmin(admin.ModelAdmin):
    list_display = [
        'supplier', 'period_year', 'period_month',
        'orders_count', 'quality_score', 'on_time_rate', 'defect_rate',
    ]
    list_filter = ['period_year', 'supplier']
    search_fields = ['supplier__name']
