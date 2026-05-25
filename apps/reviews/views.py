from django.db.models import Avg, Count, Q
from rest_framework import generics, status, filters
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsAdmin, IsActiveVendor
from core.pagination import StandardPagination
from .models import ProductReview, ReviewImage, StoreReview, ReviewHelpful
from .serializers import (
    ProductReviewSerializer, ReviewRatingSummarySerializer,
    StoreReviewSerializer, VendorReplySerializer,
)


@extend_schema(tags=['reviews'])
class ProductReviewListView(generics.ListAPIView):
    serializer_class = ProductReviewSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get_queryset(self):
        product_slug = self.kwargs['slug']
        qs = ProductReview.objects.filter(
            product__slug=product_slug, is_approved=True
        ).select_related('user').prefetch_related('images', 'helpful_votes')

        rating = self.request.query_params.get('rating')
        with_images = self.request.query_params.get('with_images')
        verified = self.request.query_params.get('verified')
        ordering = self.request.query_params.get('ordering', 'recent')

        if rating:
            qs = qs.filter(rating=rating)
        if with_images == 'true':
            qs = qs.filter(images__isnull=False).distinct()
        if verified == 'true':
            qs = qs.filter(is_verified_purchase=True)

        ordering_map = {
            'helpful': '-helpful_count',
            'rating_high': '-rating',
            'rating_low': 'rating',
            'recent': '-created_at',
            'oldest': 'created_at',
        }
        return qs.order_by(ordering_map.get(ordering, '-created_at'))


@extend_schema(tags=['reviews'])
class ProductReviewSummaryView(APIView):
    """Résumé des notes : moyenne, distribution 1-5 étoiles, compteurs."""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        qs = ProductReview.objects.filter(product__slug=slug, is_approved=True)
        agg = qs.aggregate(
            average=Avg('rating'),
            total=Count('id'),
            verified_count=Count('id', filter=Q(is_verified_purchase=True)),
            with_images_count=Count('id', filter=Q(images__isnull=False)),
        )

        distribution = {}
        for i in range(1, 6):
            distribution[str(i)] = qs.filter(rating=i).count()

        return Response({
            'average': round(agg['average'] or 0, 2),
            'total': agg['total'],
            'distribution': distribution,
            'verified_count': agg['verified_count'],
            'with_images_count': agg['with_images_count'],
        })


@extend_schema(tags=['reviews'])
class ProductReviewCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, slug):
        from apps.products.models import Product
        from apps.orders.models import OrderItem

        product = generics.get_object_or_404(Product, slug=slug, is_active=True)

        if ProductReview.objects.filter(product=product, user=request.user).exists():
            return Response(
                {'detail': 'Vous avez déjà laissé un avis pour ce produit.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        is_verified = OrderItem.objects.filter(
            product=product,
            order__user=request.user,
            order__payment_status='paid'
        ).exists()

        # Récupérer les images uploadées
        images = request.FILES.getlist('images')
        data = request.data.copy()

        serializer = ProductReviewSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save(
            user=request.user,
            product=product,
            is_verified_purchase=is_verified,
            uploaded_images=images,
        )
        return Response(
            ProductReviewSerializer(review, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


@extend_schema(tags=['reviews'])
class ProductReviewUpdateView(generics.UpdateAPIView):
    serializer_class = ProductReviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProductReview.objects.filter(user=self.request.user)


@extend_schema(tags=['reviews'])
class ProductReviewDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProductReview.objects.filter(user=self.request.user)


@extend_schema(tags=['reviews'])
class ReviewHelpfulView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        review = generics.get_object_or_404(ProductReview, pk=pk, is_approved=True)
        helpful, created = ReviewHelpful.objects.get_or_create(review=review, user=request.user)
        if not created:
            helpful.delete()
            count = review.helpful_votes.count()
            ProductReview.objects.filter(pk=pk).update(helpful_count=count)
            return Response({'voted': False, 'helpful_count': count})
        count = review.helpful_votes.count()
        ProductReview.objects.filter(pk=pk).update(helpful_count=count)
        return Response({'voted': True, 'helpful_count': count})


@extend_schema(tags=['reviews'])
class VendorReplyView(APIView):
    """Vendeur répond à un avis sur ses produits."""
    permission_classes = [IsAuthenticated, IsActiveVendor]

    def post(self, request, pk):
        review = generics.get_object_or_404(
            ProductReview, pk=pk,
            product__store__user=request.user,
            is_approved=True,
        )
        serializer = VendorReplySerializer(review, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProductReviewSerializer(review, context={'request': request}).data)


@extend_schema(tags=['reviews'])
class StoreReviewListView(generics.ListAPIView):
    serializer_class = StoreReviewSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get_queryset(self):
        return StoreReview.objects.filter(
            store__slug=self.kwargs['slug'], is_approved=True
        ).select_related('user').order_by('-created_at')


@extend_schema(tags=['reviews'])
class StoreReviewCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        from apps.vendors.models import Store
        store = generics.get_object_or_404(Store, slug=slug, status='active')
        if StoreReview.objects.filter(store=store, user=request.user).exists():
            return Response(
                {'detail': 'Vous avez déjà laissé un avis pour cette boutique.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = StoreReviewSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, store=store)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['reviews'])
class MyReviewListView(generics.ListAPIView):
    serializer_class = ProductReviewSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return ProductReview.objects.filter(
            user=self.request.user
        ).select_related('product').prefetch_related('images').order_by('-created_at')


@extend_schema(tags=['reviews'])
class AdminReviewListView(generics.ListAPIView):
    serializer_class = ProductReviewSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__email', 'user__first_name', 'product__name', 'body']

    def get_queryset(self):
        qs = ProductReview.objects.all().select_related('product', 'user').prefetch_related('images')
        is_approved = self.request.query_params.get('is_approved')
        if is_approved is not None:
            qs = qs.filter(is_approved=is_approved.lower() == 'true')
        return qs.order_by('-created_at')


@extend_schema(tags=['reviews'])
class AdminReviewApproveView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        review = generics.get_object_or_404(ProductReview, pk=pk)
        action = request.data.get('action')
        if action == 'approve':
            review.is_approved = True
        elif action == 'reject':
            review.is_approved = False
        else:
            return Response({'detail': 'Action invalide. Utilisez approve ou reject.'}, status=400)
        review.save(update_fields=['is_approved'])
        return Response(ProductReviewSerializer(review, context={'request': request}).data)

    def delete(self, request, pk):
        review = generics.get_object_or_404(ProductReview, pk=pk)
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
