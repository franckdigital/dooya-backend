from django.contrib import admin
from .models import DeliveryZone, RelayPoint, Delivery, DeliveryHistory


class DeliveryHistoryInline(admin.TabularInline):
    model = DeliveryHistory
    extra = 0
    readonly_fields = ['status', 'location', 'note', 'created_at']


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_price', 'price_per_kg', 'estimated_days', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']


@admin.register(RelayPoint)
class RelayPointAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'country', 'phone', 'is_active']
    list_filter = ['is_active', 'city']
    search_fields = ['name', 'address', 'city']


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ['tracking_number', 'order', 'delivery_person', 'type', 'status', 'estimated_delivery_date', 'created_at']
    list_filter = ['status', 'type']
    search_fields = ['tracking_number', 'order__order_number']
    readonly_fields = ['tracking_number', 'created_at', 'updated_at']
    inlines = [DeliveryHistoryInline]
