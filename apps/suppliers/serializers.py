from rest_framework import serializers
from .models import Supplier, SupplierProduct, SupplierContract, SupplierPerformanceReport


class SupplierSerializer(serializers.ModelSerializer):
    quality_rating_display = serializers.CharField(source='get_quality_rating_display', read_only=True)

    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'code', 'contact_name', 'email', 'phone', 'whatsapp',
            'address', 'city', 'country', 'website',
            'payment_terms', 'lead_time_days', 'currency', 'min_order_amount',
            'quality_rating', 'quality_rating_display', 'quality_score',
            'defect_rate', 'on_time_delivery_rate',
            'is_active', 'is_approved', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['quality_score', 'defect_rate', 'on_time_delivery_rate', 'quality_rating']


class SupplierPublicSerializer(serializers.ModelSerializer):
    """Vue limitée pour les vendeurs (pas les infos financières)."""
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'code', 'contact_name', 'email', 'phone',
            'city', 'country', 'payment_terms', 'lead_time_days',
            'quality_rating', 'quality_score', 'is_active',
        ]


class SupplierProductSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = SupplierProduct
        fields = [
            'id', 'supplier', 'supplier_name', 'product', 'product_name',
            'product_sku', 'variant', 'variant_name',
            'supplier_sku', 'unit_cost', 'currency',
            'min_order_quantity', 'lead_time_days',
            'is_preferred', 'last_price_update', 'notes',
        ]


class SupplierContractSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = SupplierContract
        fields = [
            'id', 'supplier', 'supplier_name', 'reference',
            'status', 'status_display', 'is_active',
            'start_date', 'end_date', 'terms', 'document',
            'commission_rate', 'signed_by',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['reference']


class SupplierPerformanceSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    defect_rate = serializers.ReadOnlyField()

    class Meta:
        model = SupplierPerformanceReport
        fields = [
            'id', 'supplier', 'supplier_name',
            'period_year', 'period_month',
            'orders_count', 'orders_completed', 'orders_late',
            'total_amount', 'defective_items', 'total_items_received',
            'quality_score', 'on_time_rate', 'defect_rate', 'notes',
        ]
