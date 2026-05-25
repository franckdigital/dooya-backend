from django.utils.text import slugify
from django.db.models import Q, Count, Sum
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from core.permissions import IsVendor, IsActiveVendor, IsAdmin
from core.pagination import StandardPagination
from core.utils import generate_unique_slug
from .models import Store, StoreDocument, BankAccount
from .serializers import (
    StoreSerializer, StorePublicSerializer, StoreDocumentSerializer,
    BankAccountSerializer, StoreStatsSerializer,
)


@extend_schema(tags=['vendors'])
class StoreListView(generics.ListAPIView):
    serializer_class = StorePublicSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Store.objects.filter(status='active').select_related('user')
        city = self.request.query_params.get('city')
        rating = self.request.query_params.get('rating_min')
        search = self.request.query_params.get('search')
        is_featured = self.request.query_params.get('is_featured')
        if city:
            qs = qs.filter(city__icontains=city)
        if rating:
            qs = qs.filter(rating__gte=rating)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        if is_featured:
            qs = qs.filter(is_featured=True)
        return qs.order_by('-is_featured', '-rating', '-total_sales')


@extend_schema(tags=['vendors'])
class StoreDetailView(generics.RetrieveAPIView):
    serializer_class = StorePublicSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    queryset = Store.objects.filter(status='active').select_related('user')


@extend_schema(tags=['vendors'])
class VendorStoreView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        try:
            store = Store.objects.get(user=request.user)
            serializer = StoreSerializer(store)
            return Response(serializer.data)
        except Store.DoesNotExist:
            return Response({'detail': 'Aucune boutique trouvée.'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        if Store.objects.filter(user=request.user).exists():
            return Response({'detail': 'Vous avez déjà une boutique.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = StoreSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data.get('name', '')
            slug = generate_unique_slug(Store, name)
            serializer.save(user=request.user, slug=slug)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        try:
            store = Store.objects.get(user=request.user)
        except Store.DoesNotExist:
            return Response({'detail': 'Boutique introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = StoreSerializer(store, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['vendors'])
class VendorDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        try:
            store = Store.objects.get(user=request.user)
        except Store.DoesNotExist:
            return Response({'detail': 'Boutique introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        from apps.orders.models import Order, OrderItem
        now = timezone.now()
        first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        pending_orders = OrderItem.objects.filter(store=store, order__status='pending').values('order').distinct().count()
        products_count = store.products.filter(is_active=True).count()
        this_month = OrderItem.objects.filter(store=store, order__created_at__gte=first_day, order__payment_status='paid')
        this_month_revenue = this_month.aggregate(rev=Sum('total_price'))['rev'] or 0
        this_month_orders = this_month.values('order').distinct().count()

        data = {
            'total_sales': store.total_sales,
            'total_revenue': store.total_revenue,
            'pending_orders': pending_orders,
            'products_count': products_count,
            'rating': store.rating,
            'this_month_revenue': this_month_revenue,
            'this_month_orders': this_month_orders,
        }
        serializer = StoreStatsSerializer(data)
        return Response(serializer.data)


@extend_schema(tags=['vendors'])
class StoreDocumentView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        try:
            store = Store.objects.get(user=request.user)
        except Store.DoesNotExist:
            return Response({'detail': 'Boutique introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        docs = StoreDocument.objects.filter(store=store)
        serializer = StoreDocumentSerializer(docs, many=True)
        return Response(serializer.data)

    def post(self, request):
        try:
            store = Store.objects.get(user=request.user)
        except Store.DoesNotExist:
            return Response({'detail': 'Boutique introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = StoreDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(store=store)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['vendors'])
class BankAccountView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get(self, request):
        try:
            store = Store.objects.get(user=request.user)
            account = BankAccount.objects.get(store=store)
            serializer = BankAccountSerializer(account)
            return Response(serializer.data)
        except Store.DoesNotExist:
            return Response({'detail': 'Boutique introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        except BankAccount.DoesNotExist:
            return Response({'detail': 'Aucun compte bancaire.'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        try:
            store = Store.objects.get(user=request.user)
        except Store.DoesNotExist:
            return Response({'detail': 'Boutique introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if BankAccount.objects.filter(store=store).exists():
            return Response({'detail': 'Compte bancaire déjà enregistré.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = BankAccountSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(store=store)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        try:
            store = Store.objects.get(user=request.user)
            account = BankAccount.objects.get(store=store)
        except (Store.DoesNotExist, BankAccount.DoesNotExist):
            return Response({'detail': 'Introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = BankAccountSerializer(account, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(is_verified=False)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['vendors'])
class AdminStoreListView(generics.ListAPIView):
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Store.objects.select_related('user').all()
        status_filter = self.request.query_params.get('status')
        search = self.request.query_params.get('search')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(user__email__icontains=search))
        return qs.order_by('-created_at')


@extend_schema(tags=['vendors'])
class AdminStoreActionView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        try:
            store = Store.objects.get(pk=pk)
        except Store.DoesNotExist:
            return Response({'detail': 'Boutique introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action')
        if action == 'approve':
            store.status = 'active'
            store.user.role = 'vendor'
            store.user.save(update_fields=['role'])
        elif action == 'suspend':
            store.status = 'suspended'
        elif action == 'reject':
            store.status = 'rejected'
        elif action == 'certify':
            store.is_certified = True
        elif action == 'feature':
            store.is_featured = not store.is_featured
        else:
            return Response({'detail': 'Action invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        store.save()
        serializer = StoreSerializer(store)
        return Response(serializer.data)
