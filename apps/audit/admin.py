from django.contrib import admin
from .models import MonthlySnapshot, KPIAlert, AuditReport


@admin.register(MonthlySnapshot)
class MonthlySnapshotAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'year', 'month', 'store', 'revenue', 'orders_total',
                    'new_customers', 'return_rate', 'computed_at']
    list_filter = ['year', 'month', 'store']
    search_fields = ['store__name']
    readonly_fields = ['computed_at']
    ordering = ['-year', '-month']


@admin.register(KPIAlert)
class KPIAlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'severity', 'metric_name',
                    'current_value', 'variation_pct', 'store', 'year', 'month',
                    'is_acknowledged', 'created_at']
    list_filter = ['severity', 'category', 'is_acknowledged', 'year', 'month', 'store']
    search_fields = ['title', 'metric_name']
    readonly_fields = ['acknowledged_at']
    ordering = ['-created_at']
    actions = ['acknowledge_alerts']

    def acknowledge_alerts(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(is_acknowledged=False).update(
            is_acknowledged=True,
            acknowledged_by=request.user,
            acknowledged_at=timezone.now(),
        )
        self.message_user(request, f'{updated} alerte(s) acquittée(s).')
    acknowledge_alerts.short_description = 'Acquitter les alertes sélectionnées'


@admin.register(AuditReport)
class AuditReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'report_type', 'year', 'month', 'store',
                    'generated_by', 'is_auto', 'created_at']
    list_filter = ['report_type', 'is_auto', 'year', 'month', 'store']
    search_fields = ['title']
    readonly_fields = ['data', 'key_insights', 'created_at']
    ordering = ['-created_at']
