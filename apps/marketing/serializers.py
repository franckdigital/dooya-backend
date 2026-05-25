from rest_framework import serializers
from .models import Campaign, CampaignRecipient, AbandonedCartReminder, Unsubscribe


class CampaignSerializer(serializers.ModelSerializer):
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    audience_display = serializers.CharField(source='get_audience_display', read_only=True)
    open_rate = serializers.FloatField(read_only=True)
    click_rate = serializers.FloatField(read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'channel', 'channel_display',
            'status', 'status_display', 'audience', 'audience_display',
            'subject', 'content', 'cta_url', 'cta_label',
            'scheduled_at', 'sent_at',
            'total_recipients', 'sent_count', 'opened_count', 'clicked_count', 'failed_count',
            'open_rate', 'click_rate',
            'created_by', 'created_by_name', 'created_at',
        ]
        read_only_fields = [
            'status', 'sent_at', 'total_recipients', 'sent_count',
            'opened_count', 'clicked_count', 'failed_count', 'created_by', 'created_at',
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return None


class CampaignSendSerializer(serializers.Serializer):
    """Déclenche l'envoi immédiat ou programme la campagne."""
    send_now = serializers.BooleanField(default=True)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, data):
        if not data.get('send_now') and not data.get('scheduled_at'):
            raise serializers.ValidationError('scheduled_at requis quand send_now=False.')
        return data


class AbandonedCartReminderSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    cart_item_count = serializers.SerializerMethodField()

    class Meta:
        model = AbandonedCartReminder
        fields = [
            'id', 'user', 'user_name', 'user_email', 'cart', 'cart_total',
            'status', 'status_display', 'reminder_count',
            'last_sent_at', 'converted_at', 'cart_item_count', 'created_at',
        ]
        read_only_fields = fields

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.email
        return None

    def get_cart_item_count(self, obj):
        return obj.cart.items.count()


class UnsubscribeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unsubscribe
        fields = ['id', 'channel', 'created_at']
        read_only_fields = ['created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        obj, _ = Unsubscribe.objects.get_or_create(**validated_data)
        return obj
