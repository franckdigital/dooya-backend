from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from core.permissions import IsActiveVendor, IsVendor, IsAdmin
from core.pagination import StandardPagination
from .models import Product, ProductImage, ProductVariant, ProductVideo, Tag
from .serializers import (
    ProductListSerializer, ProductDetailSerializer, ProductCreateUpdateSerializer,
    ProductImageSerializer, ProductVariantSerializer, TagSerializer,
    AdminProductWriteSerializer,
)
from .filters import ProductFilter


@extend_schema(tags=['products'])
class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'short_description', 'tags__name']
    ordering_fields = ['price', 'rating', 'created_at', 'views_count', 'reviews_count']
    ordering = ['-created_at']

    def get_queryset(self):
        return Product.objects.filter(is_active=True, store__status='active').select_related('store', 'category').prefetch_related('images')


@extend_schema(tags=['products'])
class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related('store', 'category').prefetch_related('images', 'variants', 'tags')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        from .models import ProductView
        already_viewed = ProductView.objects.filter(
            product=instance,
            session_key=session_key
        ).exists()
        if not already_viewed:
            ProductView.objects.create(
                product=instance,
                user=request.user if request.user.is_authenticated else None,
                session_key=session_key,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            Product.objects.filter(pk=instance.pk).update(views_count=instance.views_count + 1)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@extend_schema(tags=['products'])
class FeaturedProductsView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Product.objects.filter(is_active=True, is_featured=True, store__status='active').select_related('store', 'category').prefetch_related('images')[:20]


@extend_schema(tags=['products'])
class VendorProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [IsAuthenticated, IsVendor]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'sku']
    ordering_fields = ['price', 'stock', 'created_at']

    def get_queryset(self):
        return Product.objects.filter(store__user=self.request.user).select_related('store', 'category').prefetch_related('images')


@extend_schema(tags=['products'])
class VendorProductCreateView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request):
        try:
            store = request.user.store
        except Exception:
            return Response({'detail': 'Boutique introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save(store=store)
            return Response(ProductDetailSerializer(product, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['products'])
class VendorProductDetailView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get_object(self, pk, user):
        try:
            return Product.objects.get(pk=pk, store__user=user)
        except Product.DoesNotExist:
            return None

    def get(self, request, pk):
        product = self.get_object(pk, request.user)
        if not product:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProductDetailSerializer(product, context={'request': request}).data)

    def patch(self, request, pk):
        product = self.get_object(pk, request.user)
        if not product:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductCreateUpdateSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(ProductDetailSerializer(product, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        product = self.get_object(pk, request.user)
        if not product:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        product.is_active = False
        product.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['products'])
class ProductImageView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request, pk):
        try:
            product = Product.objects.get(pk=pk, store__user=request.user)
        except Product.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductImageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(product=product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, image_id):
        try:
            image = ProductImage.objects.get(pk=image_id, product__pk=pk, product__store__user=request.user)
        except ProductImage.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['products'])
class ProductVariantView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk, store__user=request.user)
        except Product.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductVariantSerializer(product.variants.all(), many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        try:
            product = Product.objects.get(pk=pk, store__user=request.user)
        except Product.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductVariantSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(product=product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk, variant_id):
        try:
            variant = ProductVariant.objects.get(pk=variant_id, product__pk=pk, product__store__user=request.user)
        except ProductVariant.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductVariantSerializer(variant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, variant_id):
        try:
            variant = ProductVariant.objects.get(pk=variant_id, product__pk=pk, product__store__user=request.user)
        except ProductVariant.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        variant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['products'])
class ProductImportView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request):
        try:
            store = request.user.store
        except Exception:
            return Response({'detail': 'Boutique introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        file = request.FILES.get('file')
        if not file:
            return Response({'detail': 'Fichier requis.'}, status=status.HTTP_400_BAD_REQUEST)
        import os
        import tempfile
        suffix = os.path.splitext(file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        from .tasks import import_products_from_csv
        task = import_products_from_csv.delay(tmp_path, store.pk)
        return Response({'task_id': task.id, 'message': "Import en cours. Vous serez notifié à la fin."}, status=status.HTTP_202_ACCEPTED)


# ── Vidéos produits ───────────────────────────────────────────────────────────

@extend_schema(tags=['products'])
class VendorProductVideoListView(APIView):
    """Liste et ajout de vidéos pour un produit (vendeur)."""
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk, store__user=request.user)
        except Product.DoesNotExist:
            return Response({'detail': 'Produit introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        from .serializers import ProductVideoSerializer
        return Response(ProductVideoSerializer(product.videos.all(), many=True, context={'request': request}).data)

    def post(self, request, pk):
        try:
            product = Product.objects.get(pk=pk, store__user=request.user)
        except Product.DoesNotExist:
            return Response({'detail': 'Produit introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        from .serializers import ProductVideoSerializer
        serializer = ProductVideoSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(product=product)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['products'])
class VendorProductVideoDetailView(APIView):
    """Modifier ou supprimer une vidéo (vendeur)."""
    permission_classes = [IsAuthenticated, IsVendor]

    def _get_video(self, request, pk, video_id):
        try:
            return ProductVideo.objects.get(pk=video_id, product__pk=pk, product__store__user=request.user)
        except ProductVideo.DoesNotExist:
            return None

    def put(self, request, pk, video_id):
        video = self._get_video(request, pk, video_id)
        if not video:
            return Response({'detail': 'Vidéo introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        from .serializers import ProductVideoSerializer
        serializer = ProductVideoSerializer(video, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk, video_id):
        video = self._get_video(request, pk, video_id)
        if not video:
            return Response({'detail': 'Vidéo introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if video.video_file:
            video.video_file.delete(save=False)
        video.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['products'])
class AdminProductListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'sku', 'store__name']
    ordering_fields = ['price', 'stock', 'created_at', 'rating']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AdminProductWriteSerializer
        return ProductListSerializer

    def get_queryset(self):
        return Product.objects.all().select_related('store', 'category').prefetch_related('images')


@extend_schema(tags=['products'])
class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Product.objects.all().select_related('store', 'category')

    def get_serializer_class(self):
        if self.request.method in ('PATCH', 'PUT'):
            return AdminProductWriteSerializer
        return ProductListSerializer


@extend_schema(tags=['products'])
class AdminProductImageView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductImageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(product=product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, image_id):
        try:
            image = ProductImage.objects.get(pk=image_id, product__pk=pk)
        except ProductImage.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['products'])
class AdminProductVariantView(APIView):
    """Create / list variants for a specific product (admin)."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(ProductVariantSerializer(product.variants.all(), many=True).data)

    def post(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductVariantSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(product=product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['products'])
class AdminVariantDetailView(APIView):
    """Update / delete a specific variant (admin)."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, variant_id):
        try:
            variant = ProductVariant.objects.get(pk=variant_id)
        except ProductVariant.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductVariantSerializer(variant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, variant_id):
        try:
            variant = ProductVariant.objects.get(pk=variant_id)
        except ProductVariant.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        variant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['products'])
class AdminTagListCreateView(generics.ListCreateAPIView):
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination
    filter_backends = [SearchFilter]
    search_fields = ['name', 'slug']
    queryset = Tag.objects.all().order_by('name')


@extend_schema(tags=['products'])
class AdminTagDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Tag.objects.all()


@extend_schema(tags=['products'])
class AdminVariantListView(generics.ListAPIView):
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination
    filter_backends = [SearchFilter]
    search_fields = ['name', 'sku', 'product__name']

    def get_queryset(self):
        return ProductVariant.objects.all().select_related('product', 'product__store')
