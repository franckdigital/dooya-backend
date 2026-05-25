from django.contrib import admin
from .models import LiveSession, LiveProduct, LiveComment, LiveViewer, LiveOrder


class LiveProductInline(admin.TabularInline):
    model = LiveProduct
    extra = 0
    fields = ['product', 'variant', 'live_price', 'discount_pct', 'is_featured', 'units_sold']
    readonly_fields = ['units_sold']


@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'store', 'host', 'status', 'scheduled_at',
                    'viewer_count', 'peak_viewer_count', 'total_orders', 'total_revenue']
    list_filter = ['status', 'store']
    search_fields = ['title', 'store__name', 'host__email']
    readonly_fields = ['stream_key', 'room_id', 'viewer_count', 'peak_viewer_count',
                       'total_orders', 'total_revenue', 'started_at', 'ended_at']
    inlines = [LiveProductInline]
    ordering = ['-scheduled_at']


@admin.register(LiveComment)
class LiveCommentAdmin(admin.ModelAdmin):
    list_display = ['session', 'user', 'comment_type', 'content', 'is_pinned', 'is_deleted', 'created_at']
    list_filter = ['comment_type', 'is_pinned', 'is_deleted', 'session']
    search_fields = ['content', 'user__email']
    ordering = ['-created_at']


@admin.register(LiveOrder)
class LiveOrderAdmin(admin.ModelAdmin):
    list_display = ['session', 'order', 'live_product', 'created_at']
    list_filter = ['session']
    ordering = ['-created_at']
