from django.contrib import admin
from .models import (
    ProductQualityProfile, QualityInspection, QualityDefect,
    QualityInspectionImage, ProductReturn, ProductReturnImage,
    SupplierQualityNotice,
)


@admin.register(ProductQualityProfile)
class ProductQualityProfileAdmin(admin.ModelAdmin):
    list_display = ['product', 'grade', 'quality_score', 'defect_rate', 'return_rate', 'total_returns']
    list_filter = ['grade']
    search_fields = ['product__name']
    readonly_fields = [
        'grade', 'quality_score', 'defect_rate', 'return_rate',
        'total_units_inspected', 'total_units_defective', 'total_returns', 'last_inspection_date',
    ]


class QualityDefectInline(admin.TabularInline):
    model = QualityDefect
    extra = 0


class QualityInspectionImageInline(admin.TabularInline):
    model = QualityInspectionImage
    extra = 0
    readonly_fields = ['image']


@admin.register(QualityInspection)
class QualityInspectionAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'product', 'inspection_type', 'result', 'grade',
        'quantity_inspected', 'quantity_failed', 'inspection_date',
    ]
    list_filter = ['inspection_type', 'result', 'grade']
    search_fields = ['reference', 'product__name', 'supplier__name']
    readonly_fields = ['reference', 'created_at']
    raw_id_fields = ['product', 'variant', 'supplier', 'order_item', 'inspector']
    inlines = [QualityDefectInline, QualityInspectionImageInline]


class ProductReturnImageInline(admin.TabularInline):
    model = ProductReturnImage
    extra = 0
    readonly_fields = ['image', 'uploaded_by', 'uploaded_at']


@admin.register(ProductReturn)
class ProductReturnAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'product', 'source', 'reason', 'condition',
        'status', 'resolution', 'stock_updated', 'restock', 'created_at',
    ]
    list_filter = ['source', 'reason', 'condition', 'status', 'resolution']
    search_fields = ['reference', 'product__name', 'requested_by__email']
    readonly_fields = ['reference', 'created_at', 'updated_at']
    raw_id_fields = [
        'requested_by', 'product', 'variant', 'order_item',
        'sav_request', 'supplier', 'dispute', 'processed_by',
    ]
    inlines = [ProductReturnImageInline]


@admin.register(SupplierQualityNotice)
class SupplierQualityNoticeAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'supplier', 'status', 'quantity_defective',
        'claim_amount', 'created_at',
    ]
    list_filter = ['status']
    search_fields = ['reference', 'supplier__name']
    readonly_fields = ['reference', 'created_at']
    raw_id_fields = ['supplier', 'inspection', 'product_return', 'dispute', 'created_by']
