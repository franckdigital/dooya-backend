from rest_framework import serializers
from .models import Store, StoreDocument, BankAccount


class StoreSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='user.full_name', read_only=True)
    owner_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Store
        fields = [
            'id', 'user', 'owner_name', 'owner_email', 'name', 'slug',
            'description', 'logo', 'banner', 'address', 'city', 'country',
            'phone', 'email', 'website', 'status', 'commission_rate',
            'is_certified', 'is_featured', 'rating', 'total_sales',
            'total_revenue', 'created_at', 'updated_at',
        ]
        read_only_fields = ['user', 'slug', 'status', 'commission_rate', 'is_certified',
                            'is_featured', 'rating', 'total_sales', 'total_revenue',
                            'created_at', 'updated_at']


class StorePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'slug', 'description', 'logo', 'banner',
            'city', 'country', 'rating', 'total_sales', 'is_certified',
            'is_featured', 'created_at',
        ]


class StoreDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoreDocument
        fields = ['id', 'store', 'document_type', 'file', 'is_verified', 'created_at']
        read_only_fields = ['store', 'is_verified', 'created_at']


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'bank_name', 'account_name', 'account_number', 'iban', 'is_verified']
        read_only_fields = ['is_verified']


class StoreStatsSerializer(serializers.Serializer):
    total_sales = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    pending_orders = serializers.IntegerField()
    products_count = serializers.IntegerField()
    rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    this_month_revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    this_month_orders = serializers.IntegerField()
