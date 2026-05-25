from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from . import engine


def _serialize_products(products, request):
    from apps.products.serializers import ProductListSerializer
    return ProductListSerializer(products, many=True, context={'request': request}).data


class SimilarProductsView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Recommandations'],
        summary='Produits similaires à un produit donné',
        parameters=[
            OpenApiParameter('limit', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request, slug):
        from apps.products.models import Product
        try:
            product = Product.objects.get(slug=slug, is_active=True)
        except Product.DoesNotExist:
            return Response({'detail': 'Produit introuvable.'}, status=404)
        limit = min(int(request.query_params.get('limit', 10)), 20)
        products = engine.similar_products(product, limit=limit)
        return Response(_serialize_products(products, request))


class PersonalizedView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Recommandations'],
        summary='Recommandations personnalisées pour l\'utilisateur connecté',
        parameters=[
            OpenApiParameter('limit', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request):
        limit = min(int(request.query_params.get('limit', 10)), 20)
        products = engine.personalized(request.user, limit=limit)
        return Response(_serialize_products(products, request))


class TrendingView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Recommandations'],
        summary='Produits tendance (derniers 7 jours par défaut)',
        parameters=[
            OpenApiParameter('limit', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('days', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('category_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request):
        limit = min(int(request.query_params.get('limit', 10)), 30)
        days = min(int(request.query_params.get('days', 7)), 90)
        category_id = request.query_params.get('category_id')
        products = engine.trending(limit=limit, days=days, category_id=category_id)
        return Response(_serialize_products(products, request))


class RecentlyViewedView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Recommandations'],
        summary='Produits récemment vus par l\'utilisateur',
        parameters=[
            OpenApiParameter('limit', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request):
        limit = min(int(request.query_params.get('limit', 10)), 20)
        products = engine.recently_viewed(request.user, limit=limit)
        return Response(_serialize_products(products, request))


class FrequentlyBoughtTogetherView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Recommandations'],
        summary='Fréquemment achetés ensemble avec ce produit',
        parameters=[
            OpenApiParameter('limit', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request, slug):
        from apps.products.models import Product
        try:
            product = Product.objects.get(slug=slug, is_active=True)
        except Product.DoesNotExist:
            return Response({'detail': 'Produit introuvable.'}, status=404)
        limit = min(int(request.query_params.get('limit', 5)), 10)
        products = engine.frequently_bought_together(product, limit=limit)
        return Response(_serialize_products(products, request))


class TrendingByStoreView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Recommandations'],
        summary='Produits tendance d\'une boutique',
        parameters=[
            OpenApiParameter('limit', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('days', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request, slug):
        from apps.vendors.models import Store
        try:
            store = Store.objects.get(slug=slug)
        except Store.DoesNotExist:
            return Response({'detail': 'Boutique introuvable.'}, status=404)
        limit = min(int(request.query_params.get('limit', 10)), 30)
        days = min(int(request.query_params.get('days', 30)), 90)
        products = engine.trending_by_store(store, limit=limit, days=days)
        return Response(_serialize_products(products, request))
