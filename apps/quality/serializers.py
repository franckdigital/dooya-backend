from rest_framework import serializers
from .models import (
    ProductQualityProfile, QualityInspection, QualityDefect,
    QualityInspectionImage, ProductReturn, ProductReturnImage,
    SupplierQualityNotice,
)


class ProductQualityProfileSerializer(serializers.ModelSerializer):
    grade_display = serializers.CharField(source='get_grade_display', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = ProductQualityProfile
        fields = [
            'id', 'product', 'product_name', 'grade', 'grade_display',
            'quality_score', 'defect_rate', 'return_rate',
            'total_units_inspected', 'total_units_defective',
            'total_returns', 'total_sales',
            'last_inspection_date', 'notes',
        ]
        read_only_fields = [
            'grade', 'quality_score', 'defect_rate', 'return_rate',
            'total_units_inspected', 'total_units_defective',
            'total_returns', 'last_inspection_date',
        ]


class QualityDefectSerializer(serializers.ModelSerializer):
    defect_type_display = serializers.CharField(source='get_defect_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)

    class Meta:
        model = QualityDefect
        fields = [
            'id', 'defect_type', 'defect_type_display',
            'severity', 'severity_display',
            'description', 'quantity_affected',
        ]


class QualityInspectionImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityInspectionImage
        fields = ['id', 'image', 'caption', 'order']


class QualityInspectionSerializer(serializers.ModelSerializer):
    defects = QualityDefectSerializer(many=True, read_only=True)
    images = QualityInspectionImageSerializer(many=True, read_only=True)
    result_display = serializers.CharField(source='get_result_display', read_only=True)
    inspection_type_display = serializers.CharField(source='get_inspection_type_display', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    pass_rate = serializers.ReadOnlyField()
    inspector_name = serializers.CharField(source='inspector.get_full_name', read_only=True)

    # Images à uploader
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )

    class Meta:
        model = QualityInspection
        fields = [
            'id', 'reference',
            'inspection_type', 'inspection_type_display',
            'product', 'product_name', 'variant',
            'supplier', 'supplier_name',
            'supplier_order_item', 'order_item', 'product_return',
            'quantity_inspected', 'quantity_passed', 'quantity_failed',
            'result', 'result_display', 'grade', 'pass_rate',
            'inspection_date', 'inspector', 'inspector_name',
            'notes', 'recommendations',
            'defects', 'images', 'uploaded_images',
            'created_at',
        ]
        read_only_fields = ['reference', 'pass_rate']

    def create(self, validated_data):
        images = validated_data.pop('uploaded_images', [])
        inspection = QualityInspection.objects.create(**validated_data)
        for idx, img in enumerate(images):
            QualityInspectionImage.objects.create(inspection=inspection, image=img, order=idx)
        return inspection


class ProductReturnImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReturnImage
        fields = ['id', 'image', 'caption', 'order', 'uploaded_at']


class ProductReturnSerializer(serializers.ModelSerializer):
    """Lecture — vue complète d'un retour."""
    images = ProductReturnImageSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    condition_display = serializers.CharField(source='get_condition_display', read_only=True)
    resolution_display = serializers.SerializerMethodField()
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    order_number = serializers.SerializerMethodField()
    inspection_result = serializers.SerializerMethodField()
    requester_name = serializers.SerializerMethodField()

    class Meta:
        model = ProductReturn
        fields = [
            'id', 'reference', 'source',
            'requested_by', 'requester_name',
            'product', 'product_name', 'variant', 'variant_name', 'quantity',
            'order_item', 'order_number',
            'sav_request', 'supplier', 'supplier_order_item',
            'reason', 'reason_display', 'description',
            'condition', 'condition_display',
            'status', 'status_display',
            'resolution', 'resolution_display', 'resolution_notes',
            'stock_updated', 'restock',
            'replacement_product', 'replacement_variant', 'replacement_tracking',
            'refund_amount', 'refunded_at',
            'dispute',
            'processed_by', 'processed_at',
            'return_tracking_number',
            'images', 'inspection_result',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'reference', 'status', 'resolution', 'resolution_notes',
            'stock_updated', 'restock', 'processed_by', 'processed_at',
            'refund_amount', 'refunded_at', 'dispute',
        ]

    def get_order_number(self, obj):
        return obj.order_item.order.order_number if obj.order_item else None

    def get_requester_name(self, obj):
        if obj.requested_by:
            return obj.requested_by.get_full_name() or obj.requested_by.email
        return None

    def get_resolution_display(self, obj):
        return obj.get_resolution_display() if obj.resolution else None

    def get_inspection_result(self, obj):
        try:
            return {
                'reference': obj.inspection.reference,
                'result': obj.inspection.result,
                'grade': obj.inspection.grade,
                'pass_rate': obj.inspection.pass_rate,
            }
        except Exception:
            return None


class ProductReturnCreateSerializer(serializers.ModelSerializer):
    """Écriture — création d'un retour par le client avec images."""
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False,
        help_text='Photos du produit à retourner (multipart)'
    )

    class Meta:
        model = ProductReturn
        fields = [
            'order_item', 'product', 'variant', 'quantity',
            'reason', 'description', 'condition',
            'sav_request', 'supplier',
            'uploaded_images',
        ]

    def validate(self, attrs):
        order_item = attrs.get('order_item')
        product = attrs.get('product')
        if order_item and order_item.product != product:
            raise serializers.ValidationError(
                'Le produit ne correspond pas à l\'article de la commande.'
            )
        return attrs

    def create(self, validated_data):
        images = validated_data.pop('uploaded_images', [])
        ret = ProductReturn.objects.create(**validated_data)
        for idx, img in enumerate(images):
            ProductReturnImage.objects.create(
                product_return=ret,
                image=img,
                order=idx,
                uploaded_by=self.context['request'].user,
            )
        return ret


class ProductReturnProcessSerializer(serializers.Serializer):
    """Corps de la requête POST /returns/<pk>/process/ (admin/vendeur)."""
    approved = serializers.BooleanField()
    restock = serializers.BooleanField(default=False)
    resolution = serializers.ChoiceField(choices=ProductReturn.RESOLUTION_CHOICES)
    resolution_notes = serializers.CharField(required=False, allow_blank=True)
    refund_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    create_replacement = serializers.BooleanField(default=False)
    replacement_product = serializers.IntegerField(required=False, allow_null=True)
    replacement_variant = serializers.IntegerField(required=False, allow_null=True)


class SupplierQualityNoticeSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    inspection_reference = serializers.CharField(source='inspection.reference', read_only=True)

    class Meta:
        model = SupplierQualityNotice
        fields = [
            'id', 'reference',
            'supplier', 'supplier_name',
            'inspection', 'inspection_reference',
            'product_return', 'dispute',
            'subject', 'description',
            'status', 'status_display',
            'quantity_defective', 'claim_amount',
            'supplier_response', 'supplier_responded_at',
            'resolution_notes', 'resolved_at',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'reference', 'supplier_response', 'supplier_responded_at',
            'resolved_at', 'created_by',
        ]
