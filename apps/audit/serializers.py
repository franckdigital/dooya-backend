from rest_framework import serializers
from .models import MonthlySnapshot, KPIAlert, AuditReport


class MonthlySnapshotSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True, default='Global')

    class Meta:
        model = MonthlySnapshot
        fields = [
            'id', 'year', 'month', 'store', 'store_name',
            'revenue', 'orders_total', 'orders_completed', 'orders_cancelled',
            'orders_refunded', 'orders_pending', 'average_order_value',
            'commissions', 'conversion_rate',
            'new_customers', 'returning_customers', 'total_active_customers',
            'cart_abandonment_rate', 'avg_purchase_frequency',
            'units_sold', 'unique_products_sold', 'stockout_products',
            'returns_count', 'return_rate', 'disputes_opened', 'disputes_resolved',
            'failed_inspections',
            'avg_delivery_days', 'on_time_delivery_rate',
            'avg_product_rating', 'reviews_count',
            'support_tickets', 'avg_ticket_resolution_days',
            'computed_at',
        ]
        read_only_fields = fields


class KPIAlertSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True, default=None)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    acknowledged_by_name = serializers.SerializerMethodField()

    class Meta:
        model = KPIAlert
        fields = [
            'id', 'title', 'description', 'recommendations',
            'category', 'category_display', 'severity', 'severity_display',
            'metric_name', 'current_value', 'previous_value', 'variation_pct', 'threshold',
            'store', 'store_name', 'year', 'month',
            'is_acknowledged', 'acknowledged_by', 'acknowledged_by_name', 'acknowledged_at',
            'created_at',
        ]
        read_only_fields = [
            'title', 'description', 'recommendations', 'category', 'severity',
            'metric_name', 'current_value', 'previous_value', 'variation_pct', 'threshold',
            'store', 'year', 'month', 'acknowledged_by', 'acknowledged_at', 'created_at',
        ]

    def get_acknowledged_by_name(self, obj):
        if obj.acknowledged_by:
            return obj.acknowledged_by.get_full_name() or obj.acknowledged_by.email
        return None


class KPIAlertAcknowledgeSerializer(serializers.Serializer):
    pass


class AuditReportSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True, default='Global')
    generated_by_name = serializers.SerializerMethodField()
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)

    class Meta:
        model = AuditReport
        fields = [
            'id', 'title', 'report_type', 'report_type_display',
            'year', 'month', 'compare_year', 'compare_month',
            'store', 'store_name', 'generated_by', 'generated_by_name',
            'data', 'summary', 'key_insights',
            'is_auto', 'pdf_file',
            'created_at',
        ]
        read_only_fields = [
            'data', 'summary', 'key_insights', 'is_auto',
            'generated_by', 'created_at',
        ]

    def get_generated_by_name(self, obj):
        if obj.generated_by:
            return obj.generated_by.get_full_name() or obj.generated_by.email
        return None


class GenerateReportSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=AuditReport.REPORT_TYPE_CHOICES)
    year = serializers.IntegerField(min_value=2020, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)
    compare_year = serializers.IntegerField(min_value=2020, max_value=2100, required=False)
    compare_month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    store_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, data):
        compare_year = data.get('compare_year')
        compare_month = data.get('compare_month')
        if (compare_year is None) != (compare_month is None):
            raise serializers.ValidationError(
                'compare_year et compare_month doivent être fournis ensemble.'
            )
        return data


class KPIMetricSerializer(serializers.Serializer):
    """Represents a single KPI with current value, previous value, and variation."""
    label = serializers.CharField()
    current = serializers.FloatField()
    previous = serializers.FloatField()
    variation_pct = serializers.FloatField()
    trend = serializers.CharField()
    unit = serializers.CharField(required=False, default='')


class InsightSerializer(serializers.Serializer):
    level = serializers.CharField()
    category = serializers.CharField()
    title = serializers.CharField()
    detail = serializers.CharField()
    recommendation = serializers.CharField()


class DashboardRequestSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2020, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)
    store_id = serializers.IntegerField(required=False, allow_null=True)


class MetricsRequestSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2020, max_value=2100)
    month = serializers.IntegerField(min_value=1, max_value=12)
    store_id = serializers.IntegerField(required=False, allow_null=True)
