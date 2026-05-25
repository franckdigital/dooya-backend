from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import CommissionRule, Commission, VendorPayout
from .serializers import (
    CommissionRuleSerializer,
    CommissionSerializer,
    VendorPayoutSerializer,
    CreatePayoutSerializer,
    CommissionSummarySerializer,
)
from .services import create_vendor_payout, get_vendor_commission_summary


# ── Admin — Règles de commission ──────────────────────────────────────────────

class AdminCommissionRuleListView(generics.ListCreateAPIView):
    serializer_class = CommissionRuleSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = CommissionRule.objects.select_related('store', 'category').order_by('-created_at')

    @extend_schema(tags=['Commissions'], summary='Règles de commission (liste / création)')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminCommissionRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CommissionRuleSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = CommissionRule.objects.select_related('store', 'category')

    @extend_schema(tags=['Commissions'], summary='Règle de commission — détail / modification / suppression')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# ── Admin — Commissions ───────────────────────────────────────────────────────

class AdminCommissionListView(generics.ListAPIView):
    serializer_class = CommissionSerializer
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        tags=['Commissions'],
        summary='Toutes les commissions',
        parameters=[
            OpenApiParameter('store_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('status', OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('month', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get_queryset(self):
        qs = Commission.objects.select_related('order', 'store', 'rule').order_by('-created_at')
        p = self.request.query_params
        if p.get('store_id'):
            qs = qs.filter(store_id=p['store_id'])
        if p.get('status'):
            qs = qs.filter(status=p['status'])
        if p.get('year'):
            qs = qs.filter(created_at__year=p['year'])
        if p.get('month'):
            qs = qs.filter(created_at__month=p['month'])
        return qs


class AdminCommissionSummaryView(APIView):
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        tags=['Commissions'],
        summary='Résumé global des commissions',
        parameters=[
            OpenApiParameter('store_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('month', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request):
        from apps.vendors.models import Store
        store_id = request.query_params.get('store_id')
        store = Store.objects.get(pk=store_id) if store_id else None
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        summary = get_vendor_commission_summary(store, year=year, month=month)
        return Response(CommissionSummarySerializer(summary).data)


# ── Admin — Reversements ──────────────────────────────────────────────────────

class AdminPayoutListView(generics.ListAPIView):
    serializer_class = VendorPayoutSerializer
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        tags=['Commissions'],
        summary='Liste des reversements vendeurs',
        parameters=[
            OpenApiParameter('store_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('status', OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get_queryset(self):
        qs = VendorPayout.objects.select_related('store', 'processed_by').order_by('-created_at')
        p = self.request.query_params
        if p.get('store_id'):
            qs = qs.filter(store_id=p['store_id'])
        if p.get('status'):
            qs = qs.filter(status=p['status'])
        return qs


class AdminCreatePayoutView(APIView):
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        tags=['Commissions'],
        summary='Créer un reversement vendeur',
        request=CreatePayoutSerializer,
        responses={201: VendorPayoutSerializer},
    )
    def post(self, request):
        serializer = CreatePayoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        from apps.vendors.models import Store
        try:
            store = Store.objects.get(pk=d['store_id'])
        except Store.DoesNotExist:
            return Response({'detail': 'Boutique introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        payout = create_vendor_payout(
            store=store,
            period_start=d['period_start'],
            period_end=d['period_end'],
            method=d['method'],
            processed_by=request.user,
        )
        if not payout:
            return Response({'detail': 'Aucune commission confirmée sur cette période.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(VendorPayoutSerializer(payout).data, status=status.HTTP_201_CREATED)


class AdminPayoutDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = VendorPayoutSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = VendorPayout.objects.select_related('store', 'processed_by')

    @extend_schema(tags=['Commissions'], summary='Détail / mise à jour d\'un reversement')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AdminMarkPayoutPaidView(APIView):
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(tags=['Commissions'], summary='Marquer un reversement comme payé')
    def post(self, request, pk):
        try:
            payout = VendorPayout.objects.get(pk=pk)
        except VendorPayout.DoesNotExist:
            return Response({'detail': 'Reversement introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if payout.status == 'paid':
            return Response({'detail': 'Déjà payé.'}, status=status.HTTP_400_BAD_REQUEST)
        payout.status = 'paid'
        payout.processed_by = request.user
        payout.processed_at = timezone.now()
        payout.payment_reference = request.data.get('payment_reference', '')
        payout.save(update_fields=['status', 'processed_by', 'processed_at', 'payment_reference'])
        return Response(VendorPayoutSerializer(payout).data)


# ── Vendeur — ses propres commissions ─────────────────────────────────────────

class VendorCommissionListView(generics.ListAPIView):
    serializer_class = CommissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Commissions'],
        summary='Mes commissions (vendeur)',
        parameters=[
            OpenApiParameter('status', OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('month', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get_queryset(self):
        store = getattr(self.request.user, 'store', None)
        if not store:
            return Commission.objects.none()
        qs = Commission.objects.filter(store=store).select_related('order').order_by('-created_at')
        p = self.request.query_params
        if p.get('status'):
            qs = qs.filter(status=p['status'])
        if p.get('year'):
            qs = qs.filter(created_at__year=p['year'])
        if p.get('month'):
            qs = qs.filter(created_at__month=p['month'])
        return qs


class VendorCommissionSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Commissions'],
        summary='Résumé de mes commissions (vendeur)',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('month', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request):
        store = getattr(request.user, 'store', None)
        if not store:
            return Response({'detail': 'Vous n\'avez pas de boutique.'}, status=status.HTTP_403_FORBIDDEN)
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        summary = get_vendor_commission_summary(store, year=year, month=month)
        return Response(CommissionSummarySerializer(summary).data)


class VendorPayoutListView(generics.ListAPIView):
    serializer_class = VendorPayoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Commissions'], summary='Mes reversements (vendeur)')
    def get_queryset(self):
        store = getattr(self.request.user, 'store', None)
        if not store:
            return VendorPayout.objects.none()
        return VendorPayout.objects.filter(store=store).order_by('-created_at')
