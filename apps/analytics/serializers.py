from rest_framework import serializers
from .models import SiteVisit, SearchQuery, SalesStat


class SiteVisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteVisit
        fields = ['id', 'user', 'page', 'ip_address', 'referrer', 'created_at']


class SearchQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchQuery
        fields = ['id', 'query', 'user', 'results_count', 'created_at']


class SalesStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesStat
        fields = ['date', 'orders_count', 'revenue', 'new_users', 'active_users']
