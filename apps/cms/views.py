from django.utils import timezone
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsAdmin
from core.pagination import StandardPagination
from core.utils import generate_unique_slug
from .models import Page, Slider, Banner, BlogCategory, BlogPost, Coupon, SidebarCard
from .serializers import (
    PageSerializer, SliderSerializer, BannerSerializer,
    BlogPostSerializer, BlogPostListSerializer, BlogCategorySerializer,
    CouponSerializer, CouponValidateSerializer, SidebarCardSerializer,
)


@extend_schema(tags=['cms'])
class PageDetailView(generics.RetrieveAPIView):
    serializer_class = PageSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    queryset = Page.objects.filter(is_published=True)


@extend_schema(tags=['cms'])
class SliderListView(generics.ListAPIView):
    serializer_class = SliderSerializer
    permission_classes = [AllowAny]
    queryset = Slider.objects.filter(is_active=True).order_by('order')


@extend_schema(tags=['cms'])
class BannerListView(generics.ListAPIView):
    serializer_class = BannerSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        now = timezone.now()
        qs = Banner.objects.filter(is_active=True).filter(
            Q(start_date__isnull=True) | Q(start_date__lte=now)
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        )
        position = self.request.query_params.get('position')
        if position:
            qs = qs.filter(position=position)
        return qs


@extend_schema(tags=['cms'])
class BannerClickView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, pk):
        try:
            banner = Banner.objects.get(pk=pk)
        except Banner.DoesNotExist:
            return Response({'detail': 'Bannière introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        Banner.objects.filter(pk=pk).update(click_count=banner.click_count + 1)
        return Response({'detail': 'Click enregistré.'})


@extend_schema(tags=['cms'])
class BlogPostListView(generics.ListAPIView):
    serializer_class = BlogPostListSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = BlogPost.objects.filter(is_published=True).select_related('author', 'category')
        category = self.request.query_params.get('category')
        tags = self.request.query_params.get('tags')
        search = self.request.query_params.get('search')
        if category:
            qs = qs.filter(category__slug=category)
        if tags:
            tag_slugs = [t.strip() for t in tags.split(',')]
            qs = qs.filter(tags__slug__in=tag_slugs).distinct()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(excerpt__icontains=search))
        return qs.order_by('-published_at')


@extend_schema(tags=['cms'])
class BlogPostDetailView(generics.RetrieveAPIView):
    serializer_class = BlogPostSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_queryset(self):
        return BlogPost.objects.filter(is_published=True).select_related('author', 'category')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        BlogPost.objects.filter(pk=instance.pk).update(views_count=instance.views_count + 1)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@extend_schema(tags=['cms'])
class CouponValidateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CouponValidateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        code = serializer.validated_data['code']
        order_amount = serializer.validated_data['order_amount']
        now = timezone.now()
        try:
            coupon = Coupon.objects.get(code=code, is_active=True, valid_from__lte=now, valid_until__gte=now)
        except Coupon.DoesNotExist:
            return Response({'valid': False, 'detail': 'Code promo invalide ou expiré.'}, status=status.HTTP_400_BAD_REQUEST)
        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            return Response({'valid': False, 'detail': 'Code promo épuisé.'}, status=status.HTTP_400_BAD_REQUEST)
        if order_amount < coupon.min_order_amount:
            return Response({'valid': False, 'detail': f'Montant minimum: {coupon.min_order_amount} XOF.'}, status=status.HTTP_400_BAD_REQUEST)
        if coupon.type == 'percentage':
            discount = min(order_amount * coupon.value / 100, coupon.max_discount or order_amount)
        else:
            discount = min(coupon.value, order_amount)
        return Response({
            'valid': True,
            'code': coupon.code,
            'type': coupon.type,
            'value': coupon.value,
            'discount': discount,
        })


@extend_schema(tags=['cms'])
class AdminPageView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        pages = Page.objects.all().order_by('-created_at')
        return Response(PageSerializer(pages, many=True).data)

    def post(self, request):
        serializer = PageSerializer(data=request.data)
        if serializer.is_valid():
            slug = generate_unique_slug(Page, serializer.validated_data['title'])
            serializer.save(slug=slug)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        try:
            page = Page.objects.get(pk=pk)
        except Page.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = PageSerializer(page, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            Page.objects.get(pk=pk).delete()
        except Page.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['cms'])
class AdminSliderView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        return Response(SliderSerializer(Slider.objects.all().order_by('order'), many=True).data)

    def post(self, request):
        serializer = SliderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        try:
            slider = Slider.objects.get(pk=pk)
        except Slider.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = SliderSerializer(slider, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            Slider.objects.get(pk=pk).delete()
        except Slider.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['cms'])
class SidebarCardListView(generics.ListAPIView):
    serializer_class = SidebarCardSerializer
    permission_classes = [AllowAny]
    queryset = SidebarCard.objects.filter(is_active=True).order_by('order')


@extend_schema(tags=['cms'])
class AdminSidebarCardView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        return Response(SidebarCardSerializer(SidebarCard.objects.all().order_by('order'), many=True).data)

    def post(self, request):
        serializer = SidebarCardSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        try:
            card = SidebarCard.objects.get(pk=pk)
        except SidebarCard.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = SidebarCardSerializer(card, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            SidebarCard.objects.get(pk=pk).delete()
        except SidebarCard.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['cms'])
class AdminBannerView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        return Response(BannerSerializer(Banner.objects.all().order_by('-created_at'), many=True).data)

    def post(self, request):
        serializer = BannerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        try:
            banner = Banner.objects.get(pk=pk)
        except Banner.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = BannerSerializer(banner, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            Banner.objects.get(pk=pk).delete()
        except Banner.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['cms'])
class AdminBlogPostView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        posts = BlogPost.objects.all().select_related('author', 'category').order_by('-created_at')
        return Response(BlogPostSerializer(posts, many=True).data)

    def post(self, request):
        serializer = BlogPostSerializer(data=request.data)
        if serializer.is_valid():
            slug = generate_unique_slug(BlogPost, serializer.validated_data['title'])
            pub_at = timezone.now() if serializer.validated_data.get('is_published') else None
            serializer.save(author=request.user, slug=slug, published_at=pub_at)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        try:
            post = BlogPost.objects.get(pk=pk)
        except BlogPost.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = BlogPostSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            if serializer.validated_data.get('is_published') and not post.published_at:
                serializer.save(published_at=timezone.now())
            else:
                serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            BlogPost.objects.get(pk=pk).delete()
        except BlogPost.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['cms'])
class AdminCouponView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        qs = Coupon.objects.all().order_by('-valid_until')
        search = request.query_params.get('search', '')
        if search:
            qs = qs.filter(Q(code__icontains=search))
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(CouponSerializer(page, many=True).data)
        return Response(CouponSerializer(qs, many=True).data)

    def post(self, request):
        serializer = CouponSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        try:
            coupon = Coupon.objects.get(pk=pk)
        except Coupon.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CouponSerializer(coupon, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            Coupon.objects.get(pk=pk).delete()
        except Coupon.DoesNotExist:
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['cms'])
class BlogCategoryListView(generics.ListAPIView):
    serializer_class = BlogCategorySerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = BlogCategory.objects.all().order_by('name')
