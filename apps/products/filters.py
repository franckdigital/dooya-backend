import django_filters
from django.utils import timezone
from .models import Product


class ProductFilter(django_filters.FilterSet):
    # ── Filtres prix ──────────────────────────────────────────────────────────
    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')

    # ── Filtres remise ─────────────────────────────────────────────────────────
    has_discount = django_filters.BooleanFilter(method='filter_has_discount')
    on_sale = django_filters.BooleanFilter(method='filter_on_sale')

    # ── Filtres stock ──────────────────────────────────────────────────────────
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')

    # ── Filtres catégorie (avec sous-catégories) ───────────────────────────────
    category = django_filters.CharFilter(method='filter_category')
    category_id = django_filters.NumberFilter(method='filter_category_id')

    # ── Filtres boutique ───────────────────────────────────────────────────────
    store = django_filters.CharFilter(field_name='store__slug', lookup_expr='exact')
    store_id = django_filters.NumberFilter(field_name='store_id', lookup_expr='exact')

    # ── Filtres tags ───────────────────────────────────────────────────────────
    tags = django_filters.CharFilter(method='filter_tags')

    # ── Filtres notation ───────────────────────────────────────────────────────
    rating_min = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')

    # ── Filtres attributs (ex: ?attr_couleur=rouge,bleu) ──────────────────────
    # Les filtres d'attributs sont traités dynamiquement dans filter_queryset

    # ── Filtres divers ─────────────────────────────────────────────────────────
    is_featured = django_filters.BooleanFilter(field_name='is_featured')
    is_digital = django_filters.BooleanFilter(field_name='is_digital')

    class Meta:
        model = Product
        fields = [
            'price_min', 'price_max', 'category', 'category_id', 'store', 'store_id',
            'in_stock', 'rating_min', 'is_featured', 'has_discount', 'on_sale',
        ]

    # ── Méthodes de filtrage ───────────────────────────────────────────────────

    def filter_category(self, queryset, name, value):
        """Filtre par slug catégorie et inclut toutes les sous-catégories."""
        from apps.categories.models import Category
        try:
            cat = Category.objects.get(slug=value, is_active=True)
            descendants = cat.get_descendants(include_self=True).values_list('id', flat=True)
            return queryset.filter(category_id__in=descendants)
        except Category.DoesNotExist:
            return queryset.none()

    def filter_category_id(self, queryset, name, value):
        """Filtre par id catégorie et inclut toutes les sous-catégories."""
        from apps.categories.models import Category
        try:
            cat = Category.objects.get(id=value, is_active=True)
            descendants = cat.get_descendants(include_self=True).values_list('id', flat=True)
            return queryset.filter(category_id__in=descendants)
        except Category.DoesNotExist:
            return queryset.none()

    def filter_in_stock(self, queryset, name, value):
        return queryset.filter(stock__gt=0) if value else queryset.filter(stock=0)

    def filter_has_discount(self, queryset, name, value):
        """Produits avec prix barré (compare_price > price)."""
        if value:
            return queryset.filter(compare_price__isnull=False, compare_price__gt=models.F('price'))
        return queryset

    def filter_on_sale(self, queryset, name, value):
        """Produits avec remise active (temporisée ou prix barré)."""
        if value:
            now = timezone.now()
            return queryset.filter(
                models.Q(compare_price__isnull=False, compare_price__gt=models.F('price')) |
                models.Q(
                    discount_value__isnull=False,
                    discount_value__gt=0,
                ) & (
                    models.Q(discount_start__isnull=True) | models.Q(discount_start__lte=now)
                ) & (
                    models.Q(discount_end__isnull=True) | models.Q(discount_end__gte=now)
                )
            ).distinct()
        return queryset

    def filter_tags(self, queryset, name, value):
        slugs = [s.strip() for s in value.split(',') if s.strip()]
        return queryset.filter(tags__slug__in=slugs).distinct()

    def filter_queryset(self, queryset):
        """Gestion dynamique des filtres d'attributs (attr_<slug>=val1,val2)."""
        queryset = super().filter_queryset(queryset)

        # Filtres attributs dynamiques : ?attr_couleur=rouge,bleu
        from apps.categories.models import Attribute
        for param, values_str in self.request.query_params.items():
            if param.startswith('attr_'):
                attr_slug = param[5:]
                values = [v.strip() for v in values_str.split(',') if v.strip()]
                if values:
                    try:
                        attr = Attribute.objects.get(slug=attr_slug)
                        queryset = queryset.filter(
                            attribute_values__attribute=attr,
                            attribute_values__value__value__in=values,
                        ).distinct()
                    except Attribute.DoesNotExist:
                        pass

        return queryset


# Nécessaire pour le filtre on_sale
from django.db import models
