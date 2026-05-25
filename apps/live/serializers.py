from rest_framework import serializers
from .models import LiveSession, LiveProduct, LiveComment, LiveViewer, LiveOrder


class LiveProductSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_slug = serializers.CharField(source='product.slug', read_only=True)
    product_image = serializers.SerializerMethodField()
    variant_name = serializers.CharField(source='variant.__str__', read_only=True, default=None)
    effective_price = serializers.SerializerMethodField()

    class Meta:
        model = LiveProduct
        fields = [
            'id', 'product', 'product_name', 'product_slug', 'product_image',
            'variant', 'variant_name',
            'live_price', 'discount_pct', 'effective_price',
            'is_featured', 'position', 'units_sold',
        ]

    def get_product_image(self, obj):
        img = obj.product.images.filter(is_primary=True).first()
        if img:
            request = self.context.get('request')
            return request.build_absolute_uri(img.image.url) if request else img.image.url
        return None

    def get_effective_price(self, obj):
        if obj.live_price:
            return float(obj.live_price)
        price = float(obj.variant.price if obj.variant else obj.product.price)
        if obj.discount_pct:
            price = price * (1 - float(obj.discount_pct) / 100)
        return round(price, 2)


class LiveProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveProduct
        fields = ['product', 'variant', 'live_price', 'discount_pct', 'position']


class LiveCommentSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_avatar = serializers.SerializerMethodField()

    class Meta:
        model = LiveComment
        fields = [
            'id', 'user', 'user_name', 'user_avatar',
            'content', 'comment_type', 'is_pinned', 'created_at',
        ]
        read_only_fields = ['user', 'is_pinned', 'created_at']

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.email
        return 'Anonyme'

    def get_user_avatar(self, obj):
        if obj.user and hasattr(obj.user, 'profile') and obj.user.profile.avatar:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.user.profile.avatar.url) if request else None
        return None


class LiveSessionListSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    host_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    featured_product = serializers.SerializerMethodField()

    class Meta:
        model = LiveSession
        fields = [
            'id', 'title', 'description', 'thumbnail',
            'store', 'store_name', 'host_name',
            'status', 'status_display', 'scheduled_at', 'started_at',
            'viewer_count', 'total_orders', 'total_revenue',
            'stream_url', 'room_id', 'featured_product',
        ]

    def get_host_name(self, obj):
        return obj.host.get_full_name() or obj.host.email

    def get_featured_product(self, obj):
        lp = obj.live_products.filter(is_featured=True).first()
        if lp:
            return LiveProductSerializer(lp, context=self.context).data
        return None


class LiveSessionDetailSerializer(LiveSessionListSerializer):
    live_products = LiveProductSerializer(many=True, read_only=True)
    recent_comments = serializers.SerializerMethodField()

    class Meta(LiveSessionListSerializer.Meta):
        fields = LiveSessionListSerializer.Meta.fields + [
            'live_products', 'recent_comments',
            'peak_viewer_count', 'is_recorded', 'recording_url',
            'stream_key',
        ]

    def get_recent_comments(self, obj):
        comments = obj.comments.filter(is_deleted=False).order_by('-created_at')[:50]
        return LiveCommentSerializer(comments, many=True, context=self.context).data


class LiveSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveSession
        fields = ['title', 'description', 'thumbnail', 'scheduled_at', 'stream_url']

    def create(self, validated_data):
        request = self.context['request']
        validated_data['host'] = request.user
        validated_data['store'] = request.user.store
        return super().create(validated_data)


class LiveSessionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveSession
        fields = ['title', 'description', 'thumbnail', 'scheduled_at', 'stream_url']
