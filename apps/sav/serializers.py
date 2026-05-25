from rest_framework import serializers
from .models import SavRequest, SavRequestImage, SavMessage, SavMessageAttachment


class SavRequestImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavRequestImage
        fields = ['id', 'image', 'order']


class SavMessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavMessageAttachment
        fields = ['id', 'file', 'filename']


class SavMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_role = serializers.CharField(source='sender.role', read_only=True)
    attachments = SavMessageAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = SavMessage
        fields = [
            'id', 'sender', 'sender_name', 'sender_role',
            'content', 'is_internal', 'attachments', 'created_at',
        ]
        read_only_fields = ['sender']


class SavRequestSerializer(serializers.ModelSerializer):
    images = SavRequestImageSerializer(many=True, read_only=True)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    product_name = serializers.CharField(source='order_item.product_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    messages = serializers.SerializerMethodField()

    def get_messages(self, obj):
        qs = obj.messages.filter(is_internal=False).select_related('sender')
        return SavMessageSerializer(qs, many=True).data

    class Meta:
        model = SavRequest
        fields = [
            'id', 'reference', 'order', 'order_number', 'order_item', 'product_name',
            'type', 'type_display', 'reason', 'reason_display', 'description',
            'status', 'status_display',
            'exchange_product', 'exchange_variant',
            'resolution_notes', 'resolved_by', 'resolved_at',
            'refund_amount', 'refund_method', 'refunded_at',
            'return_tracking_number', 'return_received_at',
            'images', 'uploaded_images', 'messages',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'reference', 'status', 'resolution_notes', 'resolved_by', 'resolved_at',
            'refund_amount', 'refund_method', 'refunded_at',
            'return_tracking_number', 'return_received_at',
        ]

    def create(self, validated_data):
        images = validated_data.pop('uploaded_images', [])
        request = SavRequest.objects.create(**validated_data)
        for idx, img in enumerate(images):
            SavRequestImage.objects.create(request=request, image=img, order=idx)
        return request


class SavRequestResolveSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavRequest
        fields = [
            'status', 'resolution_notes',
            'refund_amount', 'refund_method',
            'return_tracking_number',
        ]


class SavRequestAdminSerializer(SavRequestSerializer):
    """Serializer étendu pour l'admin avec tous les champs."""
    messages = SavMessageSerializer(many=True, read_only=True)
    user_name = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta(SavRequestSerializer.Meta):
        fields = SavRequestSerializer.Meta.fields + ['user', 'user_name', 'user_email', 'messages']
        read_only_fields = ['reference']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email if obj.user else None
