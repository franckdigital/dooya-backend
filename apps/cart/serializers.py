from rest_framework import serializers
from .models import Cart, CartItem
from apps.products.serializers import ProductListSerializer, ProductVariantSerializer


class CartItemSerializer(serializers.ModelSerializer):
    product_detail = ProductListSerializer(source='product', read_only=True)
    variant_detail = ProductVariantSerializer(source='variant', read_only=True)
    subtotal      = serializers.SerializerMethodField()
    # Flat convenience fields (used directly by the frontend)
    unit_price    = serializers.SerializerMethodField()
    product_name  = serializers.CharField(source='product.name', read_only=True)
    product_slug  = serializers.CharField(source='product.slug', read_only=True)
    product_image = serializers.SerializerMethodField()
    variant_name  = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'product_detail', 'variant', 'variant_detail', 'quantity',
            'subtotal', 'unit_price', 'product_name', 'product_slug', 'product_image', 'variant_name',
        ]
        read_only_fields = [
            'product_detail', 'variant_detail', 'subtotal',
            'unit_price', 'product_name', 'product_slug', 'product_image', 'variant_name',
        ]

    def get_subtotal(self, obj):
        return float(obj.subtotal())

    def get_unit_price(self, obj):
        price = obj.variant.price if obj.variant else obj.product.price
        return float(price)

    def get_product_image(self, obj):
        img = obj.product.primary_image
        if img and img.image:
            request = self.context.get('request')
            return request.build_absolute_uri(img.image.url) if request else img.image.url
        return None

    def get_variant_name(self, obj):
        return obj.variant.name if obj.variant else None


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price', 'items_count', 'created_at', 'updated_at']

    def get_total_price(self, obj):
        return obj.total_price()

    def get_items_count(self, obj):
        return obj.items_count()


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    variant_id = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate(self, data):
        from apps.products.models import Product, ProductVariant
        try:
            product = Product.objects.get(pk=data['product_id'], is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError({'product_id': 'Produit introuvable ou inactif.'})
        data['product'] = product
        variant = None
        if data.get('variant_id'):
            try:
                variant = ProductVariant.objects.get(pk=data['variant_id'], product=product)
            except ProductVariant.DoesNotExist:
                raise serializers.ValidationError({'variant_id': 'Variante introuvable.'})
        data['variant'] = variant
        available_stock = variant.stock if variant else product.stock
        if data['quantity'] > available_stock:
            raise serializers.ValidationError({'quantity': f'Stock insuffisant. Disponible: {available_stock}'})
        return data
