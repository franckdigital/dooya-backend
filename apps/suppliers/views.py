from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsAdmin, IsActiveVendor
from core.pagination import StandardPagination
from .models import Supplier, SupplierProduct, SupplierContract, SupplierPerformanceReport
from .serializers import (
    SupplierSerializer, SupplierPublicSerializer,
    SupplierProductSerializer, SupplierContractSerializer,
    SupplierPerformanceSerializer,
)


# ── Fournisseurs ──────────────────────────────────────────────────────────────

@extend_schema(tags=['suppliers'])
class AdminSupplierListCreateView(generics.ListCreateAPIView):
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Supplier.objects.all()
        active = self.request.query_params.get('active')
        approved = self.request.query_params.get('approved')
        search = self.request.query_params.get('search')
        if active is not None:
            qs = qs.filter(is_active=active.lower() == 'true')
        if approved is not None:
            qs = qs.filter(is_approved=approved.lower() == 'true')
        if search:
            qs = qs.filter(name__icontains=search) | qs.filter(code__icontains=search)
        return qs.order_by('name')

    def perform_create(self, serializer):
        import random, string
        code = serializer.validated_data.get('code') or (
            'SUP' + ''.join(random.choices(string.digits, k=6))
        )
        while Supplier.objects.filter(code=code).exists():
            code = 'SUP' + ''.join(random.choices(string.digits, k=6))
        serializer.save(code=code)


@extend_schema(tags=['suppliers'])
class AdminSupplierDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Supplier.objects.all()


@extend_schema(tags=['suppliers'])
class AdminSupplierApproveView(APIView):
    """Admin — homologuer ou suspendre un fournisseur."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        supplier = generics.get_object_or_404(Supplier, pk=pk)
        approve = request.data.get('approve', True)
        supplier.is_approved = bool(approve)
        supplier.save(update_fields=['is_approved'])
        action = 'homologué' if supplier.is_approved else 'suspendu'
        return Response({'detail': f'Fournisseur {action}.'})


@extend_schema(tags=['suppliers'])
class VendorSupplierListView(generics.ListAPIView):
    """Vendeur — liste les fournisseurs homologués."""
    serializer_class = SupplierPublicSerializer
    permission_classes = [IsAuthenticated, IsActiveVendor]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Supplier.objects.filter(is_active=True, is_approved=True).order_by('name')


# ── Produits fournisseurs ─────────────────────────────────────────────────────

@extend_schema(tags=['suppliers'])
class SupplierProductListCreateView(generics.ListCreateAPIView):
    serializer_class = SupplierProductSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = SupplierProduct.objects.select_related(
            'supplier', 'product', 'variant'
        )
        supplier_id = self.request.query_params.get('supplier')
        product_id = self.request.query_params.get('product')
        preferred = self.request.query_params.get('preferred')
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        if product_id:
            qs = qs.filter(product_id=product_id)
        if preferred:
            qs = qs.filter(is_preferred=True)
        return qs


@extend_schema(tags=['suppliers'])
class SupplierProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SupplierProductSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = SupplierProduct.objects.all()


@extend_schema(tags=['suppliers'])
class ProductSuppliersView(generics.ListAPIView):
    """Liste les fournisseurs d'un produit donné (admin/vendeur propriétaire)."""
    serializer_class = SupplierProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SupplierProduct.objects.filter(
            product_id=self.kwargs['product_pk']
        ).select_related('supplier').order_by('-is_preferred', 'unit_cost')


# ── Contrats ──────────────────────────────────────────────────────────────────

@extend_schema(tags=['suppliers'])
class SupplierContractListCreateView(generics.ListCreateAPIView):
    serializer_class = SupplierContractSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = SupplierContract.objects.select_related('supplier')
        supplier_id = self.request.query_params.get('supplier')
        st = self.request.query_params.get('status')
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        if st:
            qs = qs.filter(status=st)
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        import random, string
        ref = 'CTR' + ''.join(random.choices(string.digits, k=8))
        while SupplierContract.objects.filter(reference=ref).exists():
            ref = 'CTR' + ''.join(random.choices(string.digits, k=8))
        serializer.save(reference=ref, signed_by=self.request.user)


@extend_schema(tags=['suppliers'])
class SupplierContractDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = SupplierContractSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = SupplierContract.objects.all()


# ── Performance ───────────────────────────────────────────────────────────────

@extend_schema(tags=['suppliers'])
class SupplierPerformanceListView(generics.ListAPIView):
    serializer_class = SupplierPerformanceSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = SupplierPerformanceReport.objects.select_related('supplier')
        supplier_id = self.request.query_params.get('supplier')
        year = self.request.query_params.get('year')
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        if year:
            qs = qs.filter(period_year=year)
        return qs


@extend_schema(tags=['suppliers'])
class SupplierDashboardView(APIView):
    """Admin — tableau de bord fournisseurs."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        total = Supplier.objects.count()
        active = Supplier.objects.filter(is_active=True, is_approved=True).count()
        low_quality = Supplier.objects.filter(
            quality_rating__in=('D', 'F'), is_active=True
        ).count()
        pending_approval = Supplier.objects.filter(is_approved=False, is_active=True).count()

        from apps.inventory.models import SupplierOrder
        pending_orders = SupplierOrder.objects.filter(
            status__in=('sent', 'confirmed')
        ).count()

        return Response({
            'total_suppliers': total,
            'active_approved': active,
            'low_quality_suppliers': low_quality,
            'pending_approval': pending_approval,
            'pending_supplier_orders': pending_orders,
        })
