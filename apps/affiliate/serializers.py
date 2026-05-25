from rest_framework import serializers
from .models import AffiliateProfile, AffiliateLink, AffiliateConversion, AffiliatePayout


class AffiliateProfileSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = AffiliateProfile
        fields = ['id', 'user_name', 'user_email', 'code', 'commission_rate', 'total_earnings', 'total_clicks', 'total_conversions', 'is_active', 'created_at']
        read_only_fields = ['user_name', 'user_email', 'code', 'total_earnings', 'total_clicks', 'total_conversions', 'created_at']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email


class AffiliateLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = AffiliateLink
        fields = ['id', 'affiliate', 'product', 'category', 'store', 'custom_url', 'code', 'click_count', 'conversion_count', 'created_at']
        read_only_fields = ['affiliate', 'code', 'click_count', 'conversion_count', 'created_at']


class AffiliateConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AffiliateConversion
        fields = ['id', 'link', 'order', 'commission_amount', 'status', 'created_at']
        read_only_fields = ['commission_amount', 'status', 'created_at']


class AffiliateStatsSerializer(serializers.Serializer):
    total_clicks = serializers.IntegerField()
    total_conversions = serializers.IntegerField()
    total_earnings = serializers.DecimalField(max_digits=14, decimal_places=2)
    conversion_rate = serializers.FloatField()
    pending_earnings = serializers.DecimalField(max_digits=14, decimal_places=2)


class AffiliatePayoutSerializer(serializers.ModelSerializer):
    affiliate_user_name = serializers.SerializerMethodField()

    class Meta:
        model = AffiliatePayout
        fields = ['id', 'affiliate', 'affiliate_user_name', 'amount', 'method', 'account_number', 'status', 'reference', 'created_at']
        read_only_fields = ['affiliate', 'affiliate_user_name', 'status', 'reference', 'created_at']

    def get_affiliate_user_name(self, obj):
        try:
            return obj.affiliate.user.get_full_name() or obj.affiliate.user.email
        except Exception:
            return None
