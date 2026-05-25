from rest_framework import serializers
from .models import Page, Slider, Banner, BlogCategory, BlogPost, Coupon, SidebarCard


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = ['id', 'title', 'slug', 'content', 'meta_title', 'meta_description', 'is_published', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class SliderSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Slider
        fields = [
            'id', 'title', 'subtitle', 'image', 'image_url',
            'button_text', 'button_url', 'order', 'is_active',
            'badge', 'tag', 'price', 'compare_price',
            'bg_gradient', 'accent_color', 'emoji',
        ]

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class SidebarCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = SidebarCard
        fields = ['id', 'icon', 'title', 'subtitle', 'link', 'card_type', 'bg_color', 'order', 'is_active']


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ['id', 'title', 'image', 'link', 'position', 'is_active', 'start_date', 'end_date', 'click_count']
        read_only_fields = ['click_count']


class BlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ['id', 'name', 'slug']


class BlogPostListSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = BlogPost
        fields = ['id', 'title', 'slug', 'excerpt', 'image', 'author_name', 'category_name', 'views_count', 'published_at', 'created_at']


class BlogPostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = BlogPost
        fields = ['id', 'title', 'slug', 'content', 'excerpt', 'image', 'author', 'author_name', 'category', 'category_name', 'tags', 'is_published', 'published_at', 'views_count', 'meta_title', 'meta_description', 'created_at', 'updated_at']
        read_only_fields = ['author', 'author_name', 'category_name', 'views_count', 'created_at', 'updated_at']


class CouponSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Coupon
        fields = ['id', 'code', 'type', 'value', 'min_order_amount', 'max_discount', 'usage_limit', 'used_count', 'is_active', 'valid_from', 'valid_until', 'is_valid']
        read_only_fields = ['used_count', 'is_valid']


class CouponValidateSerializer(serializers.Serializer):
    code = serializers.CharField()
    order_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
