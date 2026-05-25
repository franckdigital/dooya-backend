from rest_framework import serializers
from django.db import transaction
from .models import Order, OrderItem, OrderStatusHistory, Invoice


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'variant', 'store', 'quantity', 'unit_price', 'total_price', 'product_name', 'product_image']


class OrderStatusHistorySerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = OrderStatusHistory
        fields = ['id', 'status', 'note', 'created_by', 'created_by_name', 'created_at']


class OrderListSerializer(serializers.ModelSerializer):
    items_count = serializers.SerializerMethodField()
    store_names = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()
    customer_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'status', 'payment_status',
            'total_amount', 'items_count', 'store_names',
            'customer_name', 'customer_email', 'created_at',
        ]

    def get_customer_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.email
        addr = obj.shipping_address or {}
        return addr.get('full_name', '—')

    def get_items_count(self, obj):
        return obj.items.count()

    def get_store_names(self, obj):
        return list(obj.items.values_list('store__name', flat=True).distinct())


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    customer_name  = serializers.SerializerMethodField()
    customer_email = serializers.EmailField(source='user.email', read_only=True)
    customer_phone = serializers.CharField(source='user.phone', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'user',
            'customer_name', 'customer_email', 'customer_phone',
            'status', 'payment_status',
            'shipping_address', 'notes', 'subtotal', 'shipping_cost',
            'discount', 'total_amount', 'coupon_code', 'items',
            'status_history', 'created_at', 'updated_at',
        ]

    def get_customer_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.email
        addr = obj.shipping_address or {}
        return addr.get('full_name', '—')


class OrderCreateSerializer(serializers.Serializer):
    shipping_address_id = serializers.IntegerField(required=False)
    shipping_address = serializers.JSONField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True)
    shipping_cost = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)

    def validate(self, data):
        if not data.get('shipping_address_id') and not data.get('shipping_address'):
            raise serializers.ValidationError('Une adresse de livraison est requise.')
        return data

    @transaction.atomic
    def create(self, validated_data):
        from apps.cart.models import Cart, CartItem
        from apps.products.models import Product
        from apps.cms.models import Coupon
        from django.utils import timezone

        user = self.context['request'].user
        cart = Cart.objects.filter(user=user).prefetch_related('items__product', 'items__variant').first()
        if not cart or not cart.items.exists():
            raise serializers.ValidationError('Le panier est vide.')

        address = validated_data.get('shipping_address')
        if not address and validated_data.get('shipping_address_id'):
            addr_obj = user.addresses.filter(pk=validated_data['shipping_address_id']).first()
            if not addr_obj:
                raise serializers.ValidationError('Adresse introuvable.')
            address = {
                'full_name': addr_obj.full_name,
                'phone': str(addr_obj.phone),
                'street': addr_obj.street,
                'city': addr_obj.city,
                'country': addr_obj.country,
            }

        subtotal = 0
        order_items_data = []
        for item in cart.items.all():
            unit_price = item.variant.price if item.variant else item.product.price
            available = item.variant.stock if item.variant else item.product.stock
            if item.quantity > available:
                raise serializers.ValidationError(
                    f'Stock insuffisant pour {item.product.name}: {available} disponible(s).'
                )
            total = unit_price * item.quantity
            subtotal += total
            order_items_data.append({
                'product': item.product,
                'variant': item.variant,
                'store': item.product.store,
                'quantity': item.quantity,
                'unit_price': unit_price,
                'total_price': total,
                'product_name': item.product.name,
            })

        discount = 0
        coupon_code = validated_data.get('coupon_code', '')
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, is_active=True, valid_from__lte=timezone.now(), valid_until__gte=timezone.now())
                if subtotal >= coupon.min_order_amount:
                    if coupon.type == 'percentage':
                        discount = min(subtotal * coupon.value / 100, coupon.max_discount or subtotal)
                    else:
                        discount = min(coupon.value, subtotal)
                    coupon.used_count += 1
                    coupon.save(update_fields=['used_count'])
            except Coupon.DoesNotExist:
                pass

        shipping_cost = validated_data.get('shipping_cost', 0)
        total_amount = subtotal - discount + shipping_cost

        order = Order.objects.create(
            user=user,
            shipping_address=address,
            notes=validated_data.get('notes', ''),
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            discount=discount,
            total_amount=total_amount,
            coupon_code=coupon_code,
        )

        for item_data in order_items_data:
            OrderItem.objects.create(order=order, **item_data)
            product = item_data['product']
            variant = item_data['variant']
            if variant:
                from apps.products.models import ProductVariant
                ProductVariant.objects.filter(pk=variant.pk).update(stock=variant.stock - item_data['quantity'])
            else:
                Product.objects.filter(pk=product.pk).update(stock=product.stock - item_data['quantity'])

        OrderStatusHistory.objects.create(order=order, status='pending', created_by=user)
        cart.items.all().delete()
        return order


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES, required=False)
    payment_status = serializers.ChoiceField(choices=Order.PAYMENT_STATUS_CHOICES, required=False)
    note = serializers.CharField(required=False, allow_blank=True)
