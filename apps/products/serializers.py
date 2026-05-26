from rest_framework import serializers
from .models import Product, ProductImage, ProductVariant, ProductVideo, Tag, ProductAttribute


class AdminProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'store', 'category', 'name', 'description', 'short_description',
            'price', 'compare_price', 'cost_price', 'sku', 'stock',
            'min_stock_alert', 'is_active', 'is_featured', 'is_digital', 'allow_installment',
        ]

    def create(self, validated_data):
        from core.utils import generate_unique_slug
        slug = generate_unique_slug(Product, validated_data['name'])
        return Product.objects.create(slug=slug, **validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ProductVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVideo
        fields = ['id', 'title', 'video_url', 'video_file', 'thumbnail',
                  'is_primary', 'order', 'duration_seconds', 'created_at']
        read_only_fields = ['created_at']

    def validate(self, data):
        if not data.get('video_url') and not data.get('video_file'):
            raise serializers.ValidationError('video_url ou video_file requis.')
        return data


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'order']


class ProductVariantSerializer(serializers.ModelSerializer):
    in_stock = serializers.BooleanField(read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_id = serializers.IntegerField(source='product.id', read_only=True)

    class Meta:
        model = ProductVariant
        fields = ['id', 'product_id', 'product_name', 'name', 'sku', 'price', 'compare_price', 'stock', 'in_stock', 'attributes', 'image']


class ProductAttributeSerializer(serializers.ModelSerializer):
    attribute_name = serializers.CharField(source='attribute.name', read_only=True)
    attribute_slug = serializers.CharField(source='attribute.slug', read_only=True)
    attribute_type = serializers.CharField(source='attribute.type', read_only=True)
    attribute_unit = serializers.CharField(source='attribute.unit', read_only=True)
    value_label = serializers.SerializerMethodField()
    color_hex = serializers.CharField(source='value.color_hex', read_only=True, default='')

    class Meta:
        model = ProductAttribute
        fields = [
            'id', 'attribute_name', 'attribute_slug', 'attribute_type',
            'attribute_unit', 'value_label', 'color_hex',
        ]

    def get_value_label(self, obj):
        return obj.display_value


class ProductAttributeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAttribute
        fields = ['attribute', 'value', 'custom_value']


class DiscountInfoSerializer(serializers.Serializer):
    type = serializers.CharField()
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
    start = serializers.DateTimeField(allow_null=True)
    end = serializers.DateTimeField(allow_null=True)
    percentage = serializers.IntegerField()


class ProductListSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_slug = serializers.CharField(source='store.slug', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    final_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'price', 'compare_price', 'final_price',
            'discount_percentage', 'is_on_sale', 'primary_image',
            'store_name', 'store_slug', 'category_name', 'category_slug',
            'rating', 'reviews_count', 'stock', 'in_stock', 'is_featured', 'created_at',
        ]

    def get_primary_image(self, obj):
        img = obj.primary_image
        if img and img.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(img.image.url)
            return img.image.url
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    characteristics = ProductAttributeSerializer(source='attribute_values', many=True, read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_slug = serializers.CharField(source='store.slug', read_only=True)
    store_logo = serializers.ImageField(source='store.logo', read_only=True)
    store_rating = serializers.DecimalField(source='store.rating', max_digits=3, decimal_places=2, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    category_path = serializers.SerializerMethodField()
    discount_percentage = serializers.IntegerField(read_only=True)
    final_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_on_sale = serializers.BooleanField(read_only=True)
    active_discount = serializers.SerializerMethodField()
    in_stock = serializers.BooleanField(read_only=True)
    recent_reviews = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'short_description',
            'price', 'compare_price', 'cost_price', 'final_price',
            'discount_type', 'discount_value', 'discount_start', 'discount_end',
            'active_discount', 'discount_percentage', 'is_on_sale',
            'sku', 'stock', 'in_stock', 'min_stock_alert', 'weight', 'dimensions',
            'is_active', 'is_featured', 'is_digital', 'allow_installment',
            'images', 'variants', 'tags', 'characteristics',
            'views_count', 'rating', 'reviews_count', 'recent_reviews',
            'meta_title', 'meta_description',
            'store_name', 'store_slug', 'store_logo', 'store_rating',
            'category_name', 'category_slug', 'category_path',
            'created_at', 'updated_at',
        ]

    def get_category_path(self, obj):
        if obj.category:
            return obj.category.full_path
        return None

    def get_active_discount(self, obj):
        d = obj.active_discount
        if d:
            return {
                'type': d['type'],
                'value': str(d['value']),
                'percentage': obj.discount_percentage,
                'end': obj.discount_end,
            }
        return None

    def get_recent_reviews(self, obj):
        from apps.reviews.serializers import ProductReviewSerializer
        reviews = obj.reviews.filter(is_approved=True).order_by('-created_at')[:3]
        return ProductReviewSerializer(reviews, many=True, context=self.context).data


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, write_only=True, source='tags', required=False
    )
    characteristics = ProductAttributeWriteSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Product
        fields = [
            'name', 'category', 'description', 'short_description',
            'price', 'compare_price', 'cost_price', 'sku', 'stock',
            'min_stock_alert', 'weight', 'dimensions', 'is_active', 'is_featured', 'is_digital', 'allow_installment',
            'discount_type', 'discount_value', 'discount_start', 'discount_end',
            'tag_ids', 'meta_title', 'meta_description', 'characteristics',
        ]

    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        characteristics = validated_data.pop('characteristics', [])
        from core.utils import generate_unique_slug
        slug = generate_unique_slug(Product, validated_data['name'])
        product = Product.objects.create(slug=slug, **validated_data)
        product.tags.set(tags)
        self._set_characteristics(product, characteristics)
        return product

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        characteristics = validated_data.pop('characteristics', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        if characteristics is not None:
            instance.attribute_values.all().delete()
            self._set_characteristics(instance, characteristics)
        return instance

    def _set_characteristics(self, product, characteristics):
        for item in characteristics:
            ProductAttribute.objects.create(product=product, **item)
