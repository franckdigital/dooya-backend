from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'type', 'title', 'body', 'data', 'is_read', 'channel', 'created_at']
        read_only_fields = ['type', 'title', 'body', 'data', 'channel', 'created_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            'email_order', 'email_promo', 'sms_order', 'sms_promo',
            'push_order', 'push_promo', 'whatsapp_order',
        ]
