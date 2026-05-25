from django.contrib import admin
from .models import SiteVisit, SearchQuery, SalesStat


@admin.register(SiteVisit)
class SiteVisitAdmin(admin.ModelAdmin):
    list_display = ['user', 'page', 'ip_address', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email', 'page', 'ip_address']
    readonly_fields = ['created_at']


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ['query', 'user', 'results_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['query', 'user__email']


@admin.register(SalesStat)
class SalesStatAdmin(admin.ModelAdmin):
    list_display = ['date', 'orders_count', 'revenue', 'new_users', 'active_users']
    list_filter = ['date']
    ordering = ['-date']
