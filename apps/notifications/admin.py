from django.contrib import admin
from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'title', 'channel', 'is_read', 'created_at']
    list_filter = ['type', 'channel', 'is_read']
    search_fields = ['user__email', 'title']
    readonly_fields = ['created_at']


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_order', 'sms_order', 'push_order', 'whatsapp_order']
    search_fields = ['user__email']
