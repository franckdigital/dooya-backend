from django.contrib import admin
from .models import AffiliateProfile, AffiliateLink, AffiliateClick, AffiliateConversion, AffiliatePayout


@admin.register(AffiliateProfile)
class AffiliateProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'commission_rate', 'total_earnings', 'total_clicks', 'total_conversions', 'is_active']
    list_filter = ['is_active']
    search_fields = ['user__email', 'code']
    readonly_fields = ['total_earnings', 'total_clicks', 'total_conversions']


@admin.register(AffiliateLink)
class AffiliateLinkAdmin(admin.ModelAdmin):
    list_display = ['affiliate', 'code', 'product', 'store', 'click_count', 'conversion_count']
    search_fields = ['code', 'affiliate__code']


@admin.register(AffiliateConversion)
class AffiliateConversionAdmin(admin.ModelAdmin):
    list_display = ['link', 'order', 'commission_amount', 'status', 'created_at']
    list_filter = ['status']
    list_editable = ['status']


@admin.register(AffiliatePayout)
class AffiliatePayoutAdmin(admin.ModelAdmin):
    list_display = ['affiliate', 'amount', 'method', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['affiliate__code', 'affiliate__user__email']
