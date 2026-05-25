from rest_framework import serializers
from .models import (
    FAQ, FAQCategory, SupportTicket, TicketMessage, TicketAttachment,
    Dispute, DisputeEvidence, DisputeMessage,
)




class FAQCategorySerializer(serializers.ModelSerializer):
    faqs_count = serializers.SerializerMethodField()

    class Meta:
        model = FAQCategory
        fields = ['id', 'name', 'slug', 'icon', 'order', 'faqs_count']

    def get_faqs_count(self, obj):
        return obj.faqs.filter(is_published=True).count()


class FAQSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='faq_category.name', read_only=True)

    class Meta:
        model = FAQ
        fields = [
            'id', 'faq_category', 'category_name', 'question', 'answer',
            'is_published', 'order', 'views', 'audience',
        ]


class TicketAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketAttachment
        fields = ['id', 'file', 'filename']


class TicketMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_role = serializers.CharField(source='sender.role', read_only=True)
    attachments = TicketAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = TicketMessage
        fields = [
            'id', 'sender', 'sender_name', 'sender_role',
            'content', 'is_internal', 'attachments', 'created_at',
        ]
        read_only_fields = ['sender']


class SupportTicketSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    messages_count = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'reference', 'user', 'user_name', 'user_email',
            'category', 'category_display', 'priority', 'priority_display',
            'subject', 'status', 'status_display', 'order',
            'resolved_at', 'satisfaction_score', 'messages_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['reference', 'resolved_at', 'user', 'user_name', 'user_email']

    def get_user_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.email
        return None

    def get_messages_count(self, obj):
        return obj.messages.filter(is_internal=False).count()


class SupportTicketDetailSerializer(SupportTicketSerializer):
    messages = serializers.SerializerMethodField()
    assigned_to_name = serializers.CharField(
        source='assigned_to.get_full_name', read_only=True
    )

    class Meta(SupportTicketSerializer.Meta):
        fields = SupportTicketSerializer.Meta.fields + ['messages', 'assigned_to_name']

    def get_messages(self, obj):
        user = self.context['request'].user
        qs = obj.messages.all()
        if user.role not in ('admin',):
            qs = qs.filter(is_internal=False)
        return TicketMessageSerializer(qs, many=True).data


class DisputeEvidenceSerializer(serializers.ModelSerializer):
    submitted_by_name = serializers.CharField(source='submitted_by.get_full_name', read_only=True)

    class Meta:
        model = DisputeEvidence
        fields = ['id', 'submitted_by', 'submitted_by_name', 'description', 'file', 'submitted_at']
        read_only_fields = ['submitted_by', 'submitted_at']


class DisputeMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_role = serializers.CharField(source='sender.role', read_only=True)

    class Meta:
        model = DisputeMessage
        fields = ['id', 'sender', 'sender_name', 'sender_role', 'content', 'is_internal', 'created_at']
        read_only_fields = ['sender']


class DisputeSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    complainant_name = serializers.SerializerMethodField()
    store_name = serializers.SerializerMethodField()
    order_number = serializers.SerializerMethodField()
    def get_complainant_name(self, obj):
        if obj.complainant:
            return obj.complainant.get_full_name() or obj.complainant.email
        return None

    def get_store_name(self, obj):
        return obj.defendant_store.name if obj.defendant_store else None

    def get_order_number(self, obj):
        return obj.order.order_number if obj.order else None

    class Meta:
        model = Dispute
        fields = [
            'id', 'reference', 'order', 'order_number',
            'complainant', 'complainant_name', 'defendant_store', 'store_name',
            'subject', 'description', 'status', 'status_display',
            'amount_claimed', 'amount_awarded',
            'decision_notes', 'arbitrator', 'resolved_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'reference', 'complainant', 'status', 'amount_awarded',
            'decision_notes', 'arbitrator', 'resolved_at',
        ]
        extra_kwargs = {
            'order': {'required': False, 'allow_null': True},
            'defendant_store': {'required': False, 'allow_null': True},
        }


class DisputeDetailSerializer(DisputeSerializer):
    evidences = DisputeEvidenceSerializer(many=True, read_only=True)
    messages = serializers.SerializerMethodField()

    class Meta(DisputeSerializer.Meta):
        fields = DisputeSerializer.Meta.fields + ['evidences', 'messages']

    def get_messages(self, obj):
        user = self.context['request'].user
        qs = obj.messages.all()
        if user.role not in ('admin',):
            qs = qs.filter(is_internal=False)
        return DisputeMessageSerializer(qs, many=True).data


class DisputeDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispute
        fields = ['status', 'amount_awarded', 'decision_notes']
