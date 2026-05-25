from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import MonthlySnapshot, KPIAlert, AuditReport
from .serializers import (
    MonthlySnapshotSerializer,
    KPIAlertSerializer,
    AuditReportSerializer,
    GenerateReportSerializer,
    DashboardRequestSerializer,
    MetricsRequestSerializer,
)
from core.permissions import IsAdmin
from .services import (
    compute_sales_metrics,
    compute_customer_metrics,
    compute_product_metrics,
    compute_vendor_metrics,
    compute_quality_metrics,
    compute_delivery_metrics,
    compute_support_metrics,
    compute_full_metrics,
    compare_months,
    generate_insights,
    save_monthly_snapshot,
)


def _get_store(store_id):
    if not store_id:
        return None
    from apps.vendors.models import Store
    try:
        return Store.objects.get(pk=store_id)
    except Store.DoesNotExist:
        return None


def _parse_period_params(request):
    now = timezone.now()
    try:
        year = int(request.query_params.get('year', now.year))
        month = int(request.query_params.get('month', now.month))
    except (TypeError, ValueError):
        year, month = now.year, now.month
    store_id = request.query_params.get('store_id')
    store = _get_store(store_id)
    return year, month, store


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=['Audit'],
        summary='Tableau de bord KPI — comparaison M vs M-1',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('month', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('store_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request):
        year, month, store = _parse_period_params(request)
        data = compare_months(year, month, store)
        data['insights'] = generate_insights(data)
        return Response(data)


# ── Metrics sections ──────────────────────────────────────────────────────────

class SalesMetricsView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=['Audit'],
        summary='Métriques ventes pour un mois donné',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('month', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('store_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request):
        year, month, store = _parse_period_params(request)
        return Response(compute_sales_metrics(year, month, store))


class CustomerMetricsView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=['Audit'],
        summary='Métriques comportement client',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('month', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('store_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request):
        year, month, store = _parse_period_params(request)
        return Response(compute_customer_metrics(year, month, store))


class ProductMetricsView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=['Audit'],
        summary='Métriques performance produits',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('month', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('store_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request):
        year, month, store = _parse_period_params(request)
        return Response(compute_product_metrics(year, month, store))


class VendorMetricsView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=['Audit'],
        summary='Métriques performance vendeurs',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('month', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('store_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request):
        year, month, store = _parse_period_params(request)
        return Response(compute_vendor_metrics(year, month, store))


class QualityMetricsView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=['Audit'],
        summary='Métriques qualité & retours',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('month', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('store_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request):
        year, month, store = _parse_period_params(request)
        return Response(compute_quality_metrics(year, month, store))


class DeliveryMetricsView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=['Audit'],
        summary='Métriques livraison',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('month', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('store_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request):
        year, month, store = _parse_period_params(request)
        return Response(compute_delivery_metrics(year, month, store))


class SupportMetricsView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=['Audit'],
        summary='Métriques support client',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('month', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
        ],
    )
    def get(self, request):
        now = timezone.now()
        try:
            year = int(request.query_params.get('year', now.year))
            month = int(request.query_params.get('month', now.month))
        except (TypeError, ValueError):
            year, month = now.year, now.month
        return Response(compute_support_metrics(year, month))


class FullMetricsView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=['Audit'],
        summary='Toutes les métriques combinées (ventes + clients + produits + vendeurs + qualité + livraison + support)',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('month', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('store_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request):
        year, month, store = _parse_period_params(request)
        return Response(compute_full_metrics(year, month, store))


# ── Snapshots ─────────────────────────────────────────────────────────────────

class SnapshotListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = MonthlySnapshotSerializer

    @extend_schema(
        tags=['Audit'],
        summary='Historique des snapshots mensuels',
        parameters=[
            OpenApiParameter('store_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get_queryset(self):
        qs = MonthlySnapshot.objects.select_related('store').order_by('-year', '-month')
        store_id = self.request.query_params.get('store_id')
        year = self.request.query_params.get('year')
        if store_id:
            qs = qs.filter(store_id=store_id)
        else:
            qs = qs.filter(store__isnull=True)
        if year:
            qs = qs.filter(year=year)
        return qs


class SnapshotDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdmin]
    serializer_class = MonthlySnapshotSerializer
    queryset = MonthlySnapshot.objects.select_related('store')

    @extend_schema(tags=['Audit'], summary='Détail d\'un snapshot mensuel')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ComputeSnapshotView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=['Audit'],
        summary='Calculer et sauvegarder le snapshot d\'un mois donné',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('month', OpenApiTypes.INT, location=OpenApiParameter.QUERY),
            OpenApiParameter('store_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def post(self, request):
        year, month, store = _parse_period_params(request)
        snapshot = save_monthly_snapshot(year, month, store)
        return Response(
            MonthlySnapshotSerializer(snapshot).data,
            status=status.HTTP_201_CREATED,
        )


# ── KPI Alerts ────────────────────────────────────────────────────────────────

class KPIAlertListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = KPIAlertSerializer

    @extend_schema(
        tags=['Audit'],
        summary='Liste des alertes KPI',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('month', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('severity', OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('category', OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('store_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('unacknowledged', OpenApiTypes.BOOL, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get_queryset(self):
        qs = KPIAlert.objects.select_related('store', 'acknowledged_by').order_by('-created_at')
        params = self.request.query_params
        if params.get('year'):
            qs = qs.filter(year=params['year'])
        if params.get('month'):
            qs = qs.filter(month=params['month'])
        if params.get('severity'):
            qs = qs.filter(severity=params['severity'])
        if params.get('category'):
            qs = qs.filter(category=params['category'])
        if params.get('store_id'):
            qs = qs.filter(store_id=params['store_id'])
        if params.get('unacknowledged') in ('true', '1', 'True'):
            qs = qs.filter(is_acknowledged=False)
        return qs


class KPIAlertAcknowledgeView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=['Audit'],
        summary='Acquitter une alerte KPI',
    )
    def post(self, request, pk):
        try:
            alert = KPIAlert.objects.get(pk=pk)
        except KPIAlert.DoesNotExist:
            return Response({'detail': 'Alerte introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        if alert.is_acknowledged:
            return Response({'detail': 'Alerte déjà acquittée.'}, status=status.HTTP_400_BAD_REQUEST)

        alert.is_acknowledged = True
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save(update_fields=['is_acknowledged', 'acknowledged_by', 'acknowledged_at'])
        return Response(KPIAlertSerializer(alert).data)


class KPIAlertBulkAcknowledgeView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=['Audit'],
        summary='Acquitter toutes les alertes non acquittées (optionnellement filtrées par mois)',
        parameters=[
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('month', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def post(self, request):
        qs = KPIAlert.objects.filter(is_acknowledged=False)
        if request.query_params.get('year'):
            qs = qs.filter(year=request.query_params['year'])
        if request.query_params.get('month'):
            qs = qs.filter(month=request.query_params['month'])
        count = qs.update(
            is_acknowledged=True,
            acknowledged_by=request.user,
            acknowledged_at=timezone.now(),
        )
        return Response({'acknowledged': count})


# ── Reports ───────────────────────────────────────────────────────────────────

class AuditReportListView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AuditReportSerializer

    @extend_schema(
        tags=['Audit'],
        summary='Historique des rapports d\'audit générés',
        parameters=[
            OpenApiParameter('report_type', OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('store_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('year', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get_queryset(self):
        qs = AuditReport.objects.select_related('store', 'generated_by').order_by('-created_at')
        params = self.request.query_params
        if params.get('report_type'):
            qs = qs.filter(report_type=params['report_type'])
        if params.get('store_id'):
            qs = qs.filter(store_id=params['store_id'])
        if params.get('year'):
            qs = qs.filter(year=params['year'])
        return qs


class AuditReportDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AuditReportSerializer
    queryset = AuditReport.objects.select_related('store', 'generated_by')

    @extend_schema(tags=['Audit'], summary='Détail d\'un rapport d\'audit')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class GenerateReportView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(
        tags=['Audit'],
        summary='Générer un nouveau rapport d\'audit',
        request=GenerateReportSerializer,
        responses={201: AuditReportSerializer},
    )
    def post(self, request):
        serializer = GenerateReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        store = _get_store(d.get('store_id'))
        year = d['year']
        month = d['month']
        report_type = d['report_type']
        compare_year = d.get('compare_year')
        compare_month = d.get('compare_month')

        if report_type == 'comparison':
            data = compare_months(year, month, store, compare_year, compare_month)
            insights = generate_insights(data)
        elif report_type == 'monthly':
            data = compute_full_metrics(year, month, store)
            cmp = compare_months(year, month, store)
            insights = generate_insights(cmp)
        elif report_type == 'sales':
            data = compute_sales_metrics(year, month, store)
            insights = []
        elif report_type == 'customers':
            data = compute_customer_metrics(year, month, store)
            insights = []
        elif report_type == 'vendors':
            data = compute_vendor_metrics(year, month, store)
            insights = []
        elif report_type == 'products':
            data = compute_product_metrics(year, month, store)
            insights = []
        elif report_type == 'quality':
            data = compute_quality_metrics(year, month, store)
            insights = []
        elif report_type == 'delivery':
            data = compute_delivery_metrics(year, month, store)
            insights = []
        else:
            data = {}
            insights = []

        type_label = dict(AuditReport.REPORT_TYPE_CHOICES).get(report_type, report_type)
        scope = store.name if store else 'Global'
        title = f'{type_label} — {scope} {year}/{month:02d}'

        summary_parts = []
        for insight in insights[:5]:
            summary_parts.append(f"[{insight['level'].upper()}] {insight['title']}: {insight['detail']}")
        summary = '\n'.join(summary_parts)

        report = AuditReport.objects.create(
            title=title,
            report_type=report_type,
            year=year,
            month=month,
            compare_year=compare_year,
            compare_month=compare_month,
            store=store,
            generated_by=request.user,
            data=data,
            summary=summary,
            key_insights=insights,
            is_auto=False,
        )

        return Response(AuditReportSerializer(report).data, status=status.HTTP_201_CREATED)
