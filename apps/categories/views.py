from django.db.models import Min, Max
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsAdmin
from core.pagination import StandardPagination
from core.utils import generate_unique_slug
from .models import Category, Attribute, AttributeValue
from .serializers import (
    CategorySerializer, CategoryTreeSerializer,
    AttributeSerializer, CategoryFiltersSerializer,
)


@extend_schema(tags=['categories'])
class CategoryTreeView(APIView):
    """Arbre complet des catégories actives (racines + sous-catégories récursives)."""
    permission_classes = [AllowAny]

    def get(self, request):
        roots = Category.objects.filter(parent=None, is_active=True).order_by('order', 'name')
        return Response(CategoryTreeSerializer(roots, many=True, context={'request': request}).data)


@extend_schema(tags=['categories'])
class CategoryListView(generics.ListAPIView):
    """Liste plate des catégories avec filtres parent / top_level / search."""
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Category.objects.filter(is_active=True)
        parent_id = self.request.query_params.get('parent')
        top_level = self.request.query_params.get('top_level')
        search = self.request.query_params.get('search')

        if parent_id:
            qs = qs.filter(parent_id=parent_id)
        elif top_level:
            qs = qs.filter(parent=None)

        if search:
            qs = qs.filter(name__icontains=search)

        return qs.order_by('order', 'name')


@extend_schema(tags=['categories'])
class CategoryDetailView(generics.RetrieveAPIView):
    """Détail d'une catégorie par slug, avec sous-catégories et breadcrumb."""
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    queryset = Category.objects.filter(is_active=True).prefetch_related('attributes__values')


@extend_schema(tags=['categories'])
class SubcategoryListView(APIView):
    """Sous-catégories directes d'une catégorie."""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        parent = generics.get_object_or_404(Category, slug=slug, is_active=True)
        children = parent.children.filter(is_active=True).order_by('order', 'name')
        return Response(CategorySerializer(children, many=True, context={'request': request}).data)


@extend_schema(tags=['categories'])
class CategoryFiltersView(APIView):
    """
    Retourne les filtres disponibles pour une catégorie :
    - attributs filtrables avec leurs valeurs
    - plage de prix min/max des produits
    """
    permission_classes = [AllowAny]

    def get(self, request, slug):
        cat = generics.get_object_or_404(Category, slug=slug, is_active=True)
        descendants = cat.get_descendants(include_self=True)

        # Attributs filtrables liés à cette catégorie et ses ancêtres
        cat_ids = list(descendants.values_list('id', flat=True))
        cat_ids += list(cat.get_ancestors().values_list('id', flat=True))
        attributes = Attribute.objects.filter(
            categories__id__in=cat_ids, is_filterable=True
        ).prefetch_related('values').distinct().order_by('order', 'name')

        # Plage de prix des produits actifs dans la catégorie et sous-catégories
        from apps.products.models import Product
        price_agg = Product.objects.filter(
            category__in=descendants, is_active=True
        ).aggregate(price_min=Min('price'), price_max=Max('price'))

        return Response({
            'attributes': AttributeSerializer(attributes, many=True).data,
            'price_min': price_agg['price_min'],
            'price_max': price_agg['price_max'],
        })


@extend_schema(tags=['categories'])
class CategoryProductsView(APIView):
    """Produits d'une catégorie et de toutes ses sous-catégories."""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        cat = generics.get_object_or_404(Category, slug=slug, is_active=True)
        descendants = cat.get_descendants(include_self=True)

        from apps.products.models import Product
        from apps.products.serializers import ProductListSerializer
        from apps.products.filters import ProductFilter

        qs = Product.objects.filter(
            category__in=descendants, is_active=True
        ).select_related('store', 'category')

        # Appliquer les filtres produit (prix, remise, attributs, stock…)
        filtered = ProductFilter(request.GET, queryset=qs, request=request)
        qs = filtered.qs

        # Tri
        ordering = request.query_params.get('ordering', '-created_at')
        ordering_map = {
            'price_asc': 'price', 'price_desc': '-price',
            'rating': '-rating', 'recent': '-created_at', 'popular': '-views_count',
        }
        qs = qs.order_by(ordering_map.get(ordering, '-created_at'))

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            ProductListSerializer(page, many=True, context={'request': request}).data
        )


# ── Admin CRUD ──────────────────────────────────────────────────────────────────

@extend_schema(tags=['categories'])
class AdminCategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination
    filter_backends = [SearchFilter]
    search_fields = ['name', 'slug']

    def get_queryset(self):
        return Category.objects.all().order_by('tree_id', 'lft')

    def perform_create(self, serializer):
        name = serializer.validated_data.get('name', '')
        slug = generate_unique_slug(Category, name)
        serializer.save(slug=slug)


@extend_schema(tags=['categories'])
class AdminCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Category.objects.all()


@extend_schema(tags=['categories'])
class AdminAttributeListCreateView(generics.ListCreateAPIView):
    serializer_class = AttributeSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination
    filter_backends = [SearchFilter]
    search_fields = ['name', 'slug']
    queryset = Attribute.objects.all().prefetch_related('values').order_by('order', 'name')


@extend_schema(tags=['categories'])
class AdminAttributeDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AttributeSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Attribute.objects.all()
