from rest_framework import serializers
from .models import CommissionRule, Commission, VendorPayout


class CommissionRuleSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True, default=None)
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    rate_pct = serializers.SerializerMethodField()

    class Meta:
        model = CommissionRule
        fields = ['id', 'store', 'store_name', 'category', 'category_name',
                  'rate', 'rate_pct', 'flat_fee', 'min_order_amount', 'is_active', 'note']

    def get_rate_pct(self, obj):
        return round(float(obj.rate) * 100, 2)


class CommissionSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Commission
        fields = [
            'id', 'order', 'order_number', 'store', 'store_name',
            'order_amount', 'rate_applied', 'flat_fee_applied',
            'commission_amount', 'vendor_amount',
            'status', 'status_display', 'paid_at', 'payout',
            'created_at',
        ]
        read_only_fields = fields


class VendorPayoutSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    commissions_count = serializers.SerializerMethodField()

    class Meta:
        model = VendorPayout
        fields = [
            'id', 'reference', 'store', 'store_name',
            'period_start', 'period_end',
            'total_order_amount', 'total_commission', 'total_payout',
            'status', 'status_display', 'method', 'method_display',
            'payment_reference', 'processed_by', 'processed_at',
            'commissions_count', 'notes', 'created_at',
        ]
        read_only_fields = ['reference', 'total_order_amount', 'total_commission', 'total_payout', 'created_at']

    def get_commissions_count(self, obj):
        return obj.commissions.count()


class CreatePayoutSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    method = serializers.ChoiceField(choices=VendorPayout.METHOD_CHOICES, default='bank_transfer')
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data['period_start'] > data['period_end']:
            raise serializers.ValidationError('period_start doit être avant period_end.')
        return data


class CommissionSummarySerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    total_order_amount = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    total_commission = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    total_vendor_amount = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    paid_amount = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    pending_amount = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
