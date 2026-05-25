from rest_framework import serializers
from .models import ProductReview, ReviewImage, StoreReview, ReviewHelpful


class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ['id', 'image', 'order']


class ProductReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_avatar = serializers.ImageField(source='user.avatar', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )
    has_voted = serializers.SerializerMethodField()

    class Meta:
        model = ProductReview
        fields = [
            'id', 'product', 'product_name', 'user', 'user_name', 'user_avatar', 'order',
            'rating', 'title', 'body',
            'is_verified_purchase', 'is_approved',
            'images', 'uploaded_images',
            'helpful_count', 'has_voted',
            'vendor_reply', 'vendor_replied_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'user', 'is_verified_purchase', 'is_approved',
            'helpful_count', 'vendor_reply', 'vendor_replied_at', 'created_at',
        ]

    def get_has_voted(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.helpful_votes.filter(user=request.user).exists()
        return False

    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        review = super().create(validated_data)
        for i, img in enumerate(uploaded_images[:5]):  # max 5 photos
            ReviewImage.objects.create(review=review, image=img, order=i)
        return review


class ReviewRatingSummarySerializer(serializers.Serializer):
    """Résumé des notes pour un produit (distribution 1→5 étoiles)."""
    average = serializers.DecimalField(max_digits=3, decimal_places=2)
    total = serializers.IntegerField()
    distribution = serializers.DictField(child=serializers.IntegerField())
    verified_count = serializers.IntegerField()
    with_images_count = serializers.IntegerField()


class StoreReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = StoreReview
        fields = [
            'id', 'store', 'user', 'user_name', 'user_avatar',
            'rating', 'comment', 'is_approved', 'created_at',
        ]
        read_only_fields = ['user', 'is_approved', 'created_at']


class ReviewHelpfulSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewHelpful
        fields = ['id', 'review', 'user', 'created_at']
        read_only_fields = ['user', 'created_at']


class VendorReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReview
        fields = ['vendor_reply']

    def update(self, instance, validated_data):
        from django.utils import timezone
        instance.vendor_reply = validated_data['vendor_reply']
        instance.vendor_replied_at = timezone.now()
        instance.save(update_fields=['vendor_reply', 'vendor_replied_at'])
        return instance
