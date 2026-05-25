from django.contrib import admin
from .models import (
    FAQCategory, FAQ, SupportTicket, TicketMessage,
    Dispute, DisputeEvidence, DisputeMessage,
)


@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'faq_category', 'audience', 'is_published', 'views', 'order']
    list_filter = ['faq_category', 'audience', 'is_published']
    search_fields = ['question', 'answer']


class TicketMessageInline(admin.TabularInline):
    model = TicketMessage
    extra = 0
    readonly_fields = ['sender', 'content', 'is_internal', 'created_at']
    can_delete = False


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['reference', 'user', 'category', 'priority', 'status', 'assigned_to', 'created_at']
    list_filter = ['category', 'priority', 'status']
    search_fields = ['reference', 'subject', 'user__email']
    readonly_fields = ['reference', 'created_at', 'updated_at']
    raw_id_fields = ['user', 'assigned_to', 'order']
    inlines = [TicketMessageInline]


class DisputeEvidenceInline(admin.TabularInline):
    model = DisputeEvidence
    extra = 0
    readonly_fields = ['submitted_by', 'submitted_at']


class DisputeMessageInline(admin.TabularInline):
    model = DisputeMessage
    extra = 0
    readonly_fields = ['sender', 'created_at']
    can_delete = False


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ['reference', 'complainant', 'defendant_store', 'status', 'amount_claimed', 'created_at']
    list_filter = ['status']
    search_fields = ['reference', 'subject', 'complainant__email']
    readonly_fields = ['reference', 'created_at', 'updated_at']
    raw_id_fields = ['complainant', 'defendant_store', 'order', 'arbitrator']
    inlines = [DisputeEvidenceInline, DisputeMessageInline]
