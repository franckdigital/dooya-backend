from rest_framework import serializers
from apps.products.models import Product, ProductVariant
from .models import (
    Warehouse, StockLocation, StockMovement, StockAlert,
    StockReservation, SupplierOrder, SupplierOrderItem,
)


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = [
            'id', 'name', 'code', 'address', 'city', 'country',
            'is_active', 'is_default', 'manager',
        ]


class StockLocationSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    available_quantity = serializers.ReadOnlyField()
    is_low = serializers.ReadOnlyField()

    class Meta:
        model = StockLocation
        fields = [
            'id', 'warehouse', 'warehouse_name', 'product', 'product_name', 'product_sku',
            'variant', 'variant_name', 'quantity', 'reserved_quantity',
            'available_quantity', 'is_low', 'reorder_point', 'reorder_quantity',
        ]


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    movement_type_display = serializers.CharField(source='get_movement_type_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.get_full_name', read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            'id', 'product', 'product_name', 'variant', 'variant_name',
            'warehouse', 'warehouse_name',
            'movement_type', 'movement_type_display', 'reason', 'reason_display',
            'quantity', 'stock_before', 'stock_after',
            'reference', 'order', 'performed_by', 'performed_by_name',
            'notes', 'created_at',
        ]
        read_only_fields = ['stock_before', 'stock_after']


class ManualAdjustmentSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    variant = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all(),
        required=False,
        allow_null=True,
    )
    quantity = serializers.IntegerField(help_text='Positif = entrée, Négatif = sortie')
    reason = serializers.ChoiceField(choices=StockMovement.REASON_CHOICES)
    warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(), required=False, allow_null=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class StockAlertSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = StockAlert
        fields = [
            'id', 'product', 'product_name', 'variant', 'variant_name',
            'warehouse', 'alert_type', 'alert_type_display',
            'status', 'status_display', 'current_stock', 'threshold', 'message',
            'acknowledged_by', 'acknowledged_at', 'created_at',
        ]
        read_only_fields = ['acknowledged_by', 'acknowledged_at']


class SupplierOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    total_cost = serializers.ReadOnlyField()

    class Meta:
        model = SupplierOrderItem
        fields = [
            'id', 'product', 'product_name', 'variant',
            'quantity_ordered', 'quantity_received', 'unit_cost',
            'total_cost', 'is_fully_received',
        ]


class SupplierOrderSerializer(serializers.ModelSerializer):
    items = SupplierOrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)

    class Meta:
        model = SupplierOrder
        fields = [
            'id', 'reference', 'store', 'store_name', 'warehouse',
            'supplier_name', 'supplier_contact', 'supplier_email',
            'status', 'status_display', 'expected_date', 'received_date',
            'notes', 'total_amount', 'items', 'created_at', 'updated_at',
        ]
        read_only_fields = ['reference']


class StockDashboardSerializer(serializers.Serializer):
    """Résumé stock pour le tableau de bord vendeur/admin."""
    total_products = serializers.IntegerField()
    out_of_stock = serializers.IntegerField()
    low_stock = serializers.IntegerField()
    active_alerts = serializers.IntegerField()
    total_movements_today = serializers.IntegerField()
    pending_supplier_orders = serializers.IntegerField()
