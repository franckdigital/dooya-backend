from django.contrib import admin
from .models import SavRequest, SavRequestImage, SavMessage, SavMessageAttachment


class SavRequestImageInline(admin.TabularInline):
    model = SavRequestImage
    extra = 0
    readonly_fields = ['image']


class SavMessageInline(admin.TabularInline):
    model = SavMessage
    extra = 0
    readonly_fields = ['sender', 'content', 'is_internal', 'created_at']
    can_delete = False


@admin.register(SavRequest)
class SavRequestAdmin(admin.ModelAdmin):
    list_display = ['reference', 'user', 'type', 'reason', 'status', 'created_at']
    list_filter = ['type', 'status', 'reason']
    search_fields = ['reference', 'user__email', 'order__order_number']
    readonly_fields = ['reference', 'created_at', 'updated_at']
    inlines = [SavRequestImageInline, SavMessageInline]
    raw_id_fields = ['user', 'order', 'order_item', 'resolved_by']


@admin.register(SavMessage)
class SavMessageAdmin(admin.ModelAdmin):
    list_display = ['request', 'sender', 'is_internal', 'created_at']
    list_filter = ['is_internal']
    search_fields = ['request__reference', 'sender__email']
