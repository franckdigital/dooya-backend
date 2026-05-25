from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message, MessageReaction


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    sender_avatar = serializers.ImageField(source='sender.avatar', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'sender_name', 'sender_avatar', 'content', 'type', 'file', 'is_read', 'read_at', 'created_at']
        read_only_fields = ['sender', 'is_read', 'read_at', 'created_at']


class ConversationListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    participants_detail = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'type', 'other_participant', 'participants_detail', 'last_message', 'unread_count', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        msg = obj.last_message
        if msg:
            return {'content': msg.content, 'type': msg.type, 'created_at': msg.created_at}
        return None

    def get_unread_count(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user:
            return obj.messages.filter(is_read=False).exclude(sender=user).count()
        return 0

    def get_other_participant(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if user:
            other = obj.participants.exclude(pk=user.pk).first()
            if other:
                return {'id': other.pk, 'name': other.full_name, 'avatar': str(other.avatar) if other.avatar else None}
        return None

    def get_participants_detail(self, obj):
        return [{'id': p.pk, 'name': p.full_name or p.email} for p in obj.participants.all()]


class AdminConversationListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    buyer = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'type', 'buyer', 'last_message', 'unread_count', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        msg = obj.last_message
        if msg:
            return {'content': msg.content, 'type': msg.type, 'created_at': msg.created_at}
        return None

    def get_unread_count(self, obj):
        admin = self.context.get('request').user if self.context.get('request') else None
        if admin:
            return obj.messages.filter(is_read=False).exclude(sender=admin).count()
        return 0

    def get_buyer(self, obj):
        # Prefer role=customer; fallback to any non-staff, non-admin, non-vendor participant
        buyer = obj.participants.filter(role='customer').first()
        if not buyer:
            buyer = obj.participants.filter(is_staff=False).exclude(role__in=['admin', 'vendor']).first()
        if not buyer:
            buyer = obj.participants.filter(is_staff=False).first()
        if buyer:
            return {
                'id': buyer.pk,
                'name': buyer.full_name or buyer.email,
                'email': buyer.email,
                'avatar': str(buyer.avatar) if buyer.avatar else None,
            }
        return None


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    participants_detail = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'type', 'order', 'participants', 'participants_detail', 'messages', 'created_at', 'updated_at']
        read_only_fields = ['participants', 'created_at', 'updated_at']

    def get_participants_detail(self, obj):
        return [{'id': p.pk, 'name': p.full_name} for p in obj.participants.all()]
