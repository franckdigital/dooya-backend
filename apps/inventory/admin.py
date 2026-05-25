from django.contrib import admin
from .models import (
    Warehouse, StockLocation, StockMovement, StockAlert,
    StockReservation, SupplierOrder, SupplierOrderItem,
)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'city', 'is_default', 'is_active', 'manager']
    list_filter = ['is_active', 'is_default']
    search_fields = ['name', 'code']


@admin.register(StockLocation)
class StockLocationAdmin(admin.ModelAdmin):
    list_display = ['product', 'variant', 'warehouse', 'quantity', 'reserved_quantity', 'available_quantity', 'reorder_point']
    list_filter = ['warehouse']
    search_fields = ['product__name', 'variant__name']
    raw_id_fields = ['product', 'variant']


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity', 'movement_type', 'reason', 'stock_before', 'stock_after', 'reference', 'created_at']
    list_filter = ['movement_type', 'reason']
    search_fields = ['product__name', 'reference']
    readonly_fields = ['stock_before', 'stock_after', 'created_at']
    raw_id_fields = ['product', 'variant', 'order', 'performed_by']


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ['product', 'alert_type', 'status', 'current_stock', 'threshold', 'created_at']
    list_filter = ['alert_type', 'status']
    search_fields = ['product__name']
    readonly_fields = ['created_at']


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity', 'is_confirmed', 'expires_at', 'created_at']
    list_filter = ['is_confirmed']
    search_fields = ['product__name']


class SupplierOrderItemInline(admin.TabularInline):
    model = SupplierOrderItem
    extra = 1
    raw_id_fields = ['product', 'variant']


@admin.register(SupplierOrder)
class SupplierOrderAdmin(admin.ModelAdmin):
    list_display = ['reference', 'store', 'supplier_name', 'status', 'expected_date', 'total_amount', 'created_at']
    list_filter = ['status']
    search_fields = ['reference', 'supplier_name', 'store__name']
    readonly_fields = ['reference', 'created_at', 'updated_at']
    inlines = [SupplierOrderItemInline]
