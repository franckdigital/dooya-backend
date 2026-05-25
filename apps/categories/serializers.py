from rest_framework import serializers
from .models import Category, Attribute, AttributeValue


class AttributeValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeValue
        fields = ['id', 'value', 'color_hex', 'order']


class AttributeSerializer(serializers.ModelSerializer):
    values = AttributeValueSerializer(many=True, read_only=True)

    class Meta:
        model = Attribute
        fields = ['id', 'name', 'slug', 'type', 'unit', 'is_filterable', 'is_required', 'order', 'values']


class CategoryBreadcrumbSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    full_path = serializers.ReadOnlyField()
    is_leaf = serializers.ReadOnlyField()
    products_count = serializers.ReadOnlyField()
    breadcrumb = serializers.SerializerMethodField()
    attributes = AttributeSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'parent', 'parent_name', 'image', 'icon',
            'description', 'is_active', 'order', 'full_path', 'is_leaf',
            'products_count', 'breadcrumb', 'attributes',
            'meta_title', 'meta_description',
        ]

    def get_breadcrumb(self, obj):
        ancestors = obj.get_ancestors(include_self=True)
        return CategoryBreadcrumbSerializer(ancestors, many=True).data


class RecursiveCategorySerializer(serializers.Serializer):
    def to_representation(self, instance):
        serializer = CategoryTreeSerializer(instance, context=self.context)
        return serializer.data


class CategoryTreeSerializer(serializers.ModelSerializer):
    children = RecursiveCategorySerializer(many=True, read_only=True)
    is_leaf = serializers.ReadOnlyField()
    products_count = serializers.ReadOnlyField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'image', 'icon', 'description',
            'order', 'is_leaf', 'products_count', 'children',
        ]


class CategoryFiltersSerializer(serializers.Serializer):
    """Filtres disponibles pour une catégorie (attributs + plage de prix)."""
    attributes = AttributeSerializer(many=True)
    price_min = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    price_max = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
