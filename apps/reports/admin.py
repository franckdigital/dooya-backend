from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'status', 'generated_by', 'created_at', 'completed_at']
    list_filter = ['type', 'status']
    search_fields = ['name', 'generated_by__email']
    readonly_fields = ['status', 'file', 'created_at', 'completed_at']
