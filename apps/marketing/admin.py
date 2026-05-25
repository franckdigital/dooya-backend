from django.contrib import admin
from .models import Campaign, CampaignRecipient, AbandonedCartReminder, Unsubscribe


class CampaignRecipientInline(admin.TabularInline):
    model = CampaignRecipient
    extra = 0
    readonly_fields = ['user', 'status', 'sent_at', 'opened_at', 'clicked_at']
    can_delete = False
    max_num = 0


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel', 'status', 'audience', 'total_recipients',
                    'sent_count', 'open_rate', 'click_rate', 'scheduled_at', 'sent_at']
    list_filter = ['channel', 'status', 'audience']
    search_fields = ['name', 'subject']
    readonly_fields = ['status', 'sent_at', 'total_recipients', 'sent_count',
                       'opened_count', 'clicked_count', 'failed_count']
    inlines = [CampaignRecipientInline]
    ordering = ['-created_at']
    actions = ['send_now']

    def send_now(self, request, queryset):
        from .tasks import send_campaign_task
        for campaign in queryset.filter(status__in=['draft', 'scheduled']):
            send_campaign_task.delay(campaign.pk)
        self.message_user(request, f'{queryset.count()} campagne(s) déclenchée(s).')
    send_now.short_description = 'Envoyer maintenant'


@admin.register(AbandonedCartReminder)
class AbandonedCartReminderAdmin(admin.ModelAdmin):
    list_display = ['user', 'cart_total', 'status', 'reminder_count', 'last_sent_at', 'converted_at']
    list_filter = ['status']
    search_fields = ['user__email']
    readonly_fields = ['cart', 'user', 'cart_total', 'reminder_count', 'last_sent_at', 'converted_at']
    ordering = ['-created_at']


@admin.register(Unsubscribe)
class UnsubscribeAdmin(admin.ModelAdmin):
    list_display = ['user', 'channel', 'created_at']
    list_filter = ['channel']
    search_fields = ['user__email']
