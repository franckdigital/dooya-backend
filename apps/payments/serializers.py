from rest_framework import serializers
from .models import Payment, Refund, InstallmentPlan, Installment


class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    customer_name = serializers.SerializerMethodField()

    def get_customer_name(self, obj):
        try:
            u = obj.order.user
            if not u:
                return None
            name = u.get_full_name().strip()
            return name or u.email
        except Exception:
            return None

    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'customer_name', 'amount', 'currency', 'method', 'gateway',
            'transaction_id', 'reference', 'status', 'metadata', 'paid_at', 'created_at',
        ]
        read_only_fields = ['order_number', 'customer_name', 'transaction_id', 'reference', 'status', 'paid_at', 'created_at']


class PaymentInitiateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    method = serializers.ChoiceField(choices=Payment.METHOD_CHOICES)
    gateway = serializers.ChoiceField(choices=Payment.GATEWAY_CHOICES)

    def validate_order_id(self, value):
        from apps.orders.models import Order
        request = self.context.get('request')
        try:
            order = Order.objects.get(pk=value, user=request.user)
        except Order.DoesNotExist:
            raise serializers.ValidationError('Commande introuvable.')
        if order.payment_status == 'paid':
            raise serializers.ValidationError('Cette commande est déjà payée.')
        self._order = order
        return value

    def validate(self, data):
        data['order'] = self._order
        return data


class RefundSerializer(serializers.ModelSerializer):
    order_number = serializers.SerializerMethodField()

    class Meta:
        model = Refund
        fields = ['id', 'payment', 'order_number', 'amount', 'reason', 'status', 'processed_at', 'created_at']
        read_only_fields = ['order_number', 'status', 'processed_at', 'created_at']

    def get_order_number(self, obj):
        try:
            return obj.payment.order.order_number
        except Exception:
            return None


class InstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Installment
        fields = [
            'id', 'amount', 'due_date', 'paid_at', 'status',
            'payment_method', 'proof_image', 'reference',
            'verified_at', 'rejection_reason',
        ]
        read_only_fields = ['paid_at', 'verified_at']


class InstallmentPlanSerializer(serializers.ModelSerializer):
    installments = InstallmentSerializer(many=True, read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    order_customer = serializers.SerializerMethodField()
    relay_point_name = serializers.CharField(source='relay_point.name', read_only=True)
    relay_point_address = serializers.CharField(source='relay_point.address', read_only=True)
    relay_point_city = serializers.CharField(source='relay_point.city', read_only=True)

    def get_order_customer(self, obj):
        try:
            u = obj.order.user
            return u.get_full_name() or u.email if u else '—'
        except Exception:
            return '—'

    class Meta:
        model = InstallmentPlan
        fields = [
            'id', 'order', 'order_number', 'order_customer', 'relay_point', 'relay_point_name',
            'relay_point_address', 'relay_point_city',
            'total_amount', 'down_payment', 'remaining_amount',
            'installments_count', 'frequency', 'status',
            'contract_signed', 'contract_signed_at',
            'due_date', 'extension_granted', 'extended_due_date', 'penalty_amount',
            'stock_deducted', 'stock_deducted_at',
            'installments', 'created_at',
        ]
        read_only_fields = [
            'remaining_amount', 'status', 'contract_signed', 'contract_signed_at',
            'due_date', 'extension_granted', 'extended_due_date', 'penalty_amount',
            'stock_deducted', 'stock_deducted_at', 'created_at',
        ]
