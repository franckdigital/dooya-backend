from django.db.models import Max
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsAdmin, IsActiveVendor
from core.pagination import StandardPagination
from .models import (
    ProductQualityProfile, QualityInspection, ProductReturn,
    ProductReturnImage, SupplierQualityNotice,
)
from .serializers import (
    ProductQualityProfileSerializer,
    QualityInspectionSerializer,
    ProductReturnSerializer, ProductReturnCreateSerializer, ProductReturnProcessSerializer,
    SupplierQualityNoticeSerializer,
)
from .services import process_product_return


# ── Profils qualité produit ───────────────────────────────────────────────────

@extend_schema(tags=['quality'])
class ProductQualityProfileView(generics.RetrieveUpdateAPIView):
    """Fiche qualité d'un produit (lecture publique, mise à jour admin)."""
    serializer_class = ProductQualityProfileSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsAuthenticated(), IsAdmin()]
        return []

    def get_object(self):
        from apps.products.models import Product
        product = generics.get_object_or_404(Product, pk=self.kwargs['product_pk'])
        profile, _ = ProductQualityProfile.objects.get_or_create(product=product)
        return profile


@extend_schema(tags=['quality'])
class AdminProductQualityListView(generics.ListAPIView):
    """Admin — liste tous les profils qualité avec filtres par grade."""
    serializer_class = ProductQualityProfileSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = ProductQualityProfile.objects.select_related('product')
        grade = self.request.query_params.get('grade')
        store = self.request.query_params.get('store')
        if grade:
            qs = qs.filter(grade=grade)
        if store:
            qs = qs.filter(product__store_id=store)
        return qs.order_by('grade', 'quality_score')


@extend_schema(tags=['quality'])
class VendorProductQualityListView(generics.ListAPIView):
    """Vendeur — qualité de ses propres produits."""
    serializer_class = ProductQualityProfileSerializer
    permission_classes = [IsAuthenticated, IsActiveVendor]
    pagination_class = StandardPagination

    def get_queryset(self):
        store = self.request.user.store
        return ProductQualityProfile.objects.filter(
            product__store=store
        ).select_related('product').order_by('grade', 'quality_score')


# ── Inspections qualité ───────────────────────────────────────────────────────

@extend_schema(tags=['quality'])
class QualityInspectionListCreateView(generics.ListCreateAPIView):
    serializer_class = QualityInspectionSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = QualityInspection.objects.select_related(
            'product', 'variant', 'supplier', 'inspector'
        ).prefetch_related('defects', 'images')
        for param in ('result', 'inspection_type', 'supplier', 'product'):
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{f'{param}_id' if param in ('supplier', 'product') else param: val})
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(inspection_date__gte=date_from)
        if date_to:
            qs = qs.filter(inspection_date__lte=date_to)
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(inspector=self.request.user)


@extend_schema(tags=['quality'])
class QualityInspectionDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = QualityInspectionSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = QualityInspection.objects.prefetch_related('defects', 'images')
    parser_classes = [MultiPartParser, FormParser, JSONParser]


@extend_schema(tags=['quality'])
class VendorQualityInspectionListView(generics.ListAPIView):
    """Vendeur — inspections de ses produits."""
    serializer_class = QualityInspectionSerializer
    permission_classes = [IsAuthenticated, IsActiveVendor]
    pagination_class = StandardPagination

    def get_queryset(self):
        store = self.request.user.store
        return QualityInspection.objects.filter(
            product__store=store
        ).select_related('product', 'variant').prefetch_related('defects', 'images').order_by('-created_at')


# ── Retours produits ──────────────────────────────────────────────────────────

@extend_schema(tags=['quality'])
class MyProductReturnListCreateView(generics.ListCreateAPIView):
    """
    Client — liste ses retours et en crée un nouveau.
    Supporte l'upload d'images via multipart/form-data.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductReturnCreateSerializer
        return ProductReturnSerializer

    def get_queryset(self):
        return ProductReturn.objects.filter(
            requested_by=self.request.user
        ).select_related('product', 'variant', 'order_item').prefetch_related('images').order_by('-created_at')

    def perform_create(self, serializer):
        # Vérifier que l'order_item appartient à l'utilisateur
        order_item = serializer.validated_data.get('order_item')
        if order_item and order_item.order.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cet article ne vous appartient pas.")
        serializer.save(requested_by=self.request.user, source='customer')


@extend_schema(tags=['quality'])
class MyProductReturnDetailView(generics.RetrieveAPIView):
    serializer_class = ProductReturnSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProductReturn.objects.filter(
            requested_by=self.request.user
        ).prefetch_related('images')


@extend_schema(tags=['quality'])
class ProductReturnAddImageView(APIView):
    """
    Client — ajouter des images supplémentaires à un retour en attente.
    POST multipart avec le champ 'images[]'.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        ret = generics.get_object_or_404(
            ProductReturn, pk=pk, requested_by=request.user
        )
        if ret.status not in ('pending', 'received'):
            return Response(
                {'detail': 'Impossible d\'ajouter des images à ce stade.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        images = request.FILES.getlist('images')
        if not images:
            return Response({'detail': 'Aucune image fournie.'}, status=status.HTTP_400_BAD_REQUEST)

        current_max = ret.images.aggregate(m=Max('order'))['m'] or -1

        created = []
        for idx, img in enumerate(images):
            ri = ProductReturnImage.objects.create(
                product_return=ret,
                image=img,
                order=current_max + idx + 1,
                uploaded_by=request.user,
            )
            created.append(ri.id)

        return Response(
            {'detail': f'{len(created)} image(s) ajoutée(s).', 'ids': created},
            status=status.HTTP_201_CREATED,
        )


# ── Admin retours ─────────────────────────────────────────────────────────────

@extend_schema(tags=['quality'])
class AdminProductReturnListView(generics.ListAPIView):
    serializer_class = ProductReturnSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = ProductReturn.objects.select_related(
            'requested_by', 'product', 'variant', 'order_item', 'supplier'
        ).prefetch_related('images')
        for param in ('status', 'source', 'reason', 'condition'):
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{param: val})
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(reference__icontains=search) | qs.filter(
                requested_by__email__icontains=search
            )
        return qs.order_by('-created_at')


@extend_schema(tags=['quality'])
class AdminProductReturnDetailView(generics.RetrieveAPIView):
    serializer_class = ProductReturnSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = ProductReturn.objects.prefetch_related('images')


@extend_schema(tags=['quality'])
class AdminProductReturnProcessView(APIView):
    """
    Admin — traiter un retour produit.
    Déclenche : inspection qualité + mise à jour stock + résolution.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        ret = generics.get_object_or_404(ProductReturn, pk=pk)
        if ret.status in ('completed', 'refunded', 'disposed', 'rejected'):
            return Response(
                {'detail': 'Ce retour est déjà clôturé.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ProductReturnProcessSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        d = serializer.validated_data
        updated = process_product_return(
            product_return=ret,
            approved=d['approved'],
            restock=d.get('restock', False),
            resolution=d['resolution'],
            resolution_notes=d.get('resolution_notes', ''),
            refund_amount=d.get('refund_amount'),
            processed_by=request.user,
            create_replacement=d.get('create_replacement', False),
            replacement_product_id=d.get('replacement_product'),
            replacement_variant_id=d.get('replacement_variant'),
        )
        return Response(ProductReturnSerializer(updated, context={'request': request}).data)


@extend_schema(tags=['quality'])
class AdminProductReturnAdvanceView(APIView):
    """Admin — faire avancer le statut d'un retour (après approbation)."""
    permission_classes = [IsAuthenticated, IsAdmin]

    # Transitions autorisées
    TRANSITIONS = {
        'approved':             'received',
        'received':             'under_inspection',
        'under_inspection':     'completed',
        'replacement_pending':  'replacement_sent',
        'replacement_sent':     'completed',
        'restocked':            'completed',
    }

    def post(self, request, pk):
        ret = generics.get_object_or_404(ProductReturn, pk=pk)
        next_status = self.TRANSITIONS.get(ret.status)
        if not next_status:
            return Response(
                {'detail': f'Aucune transition possible depuis "{ret.status}".'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notes = request.data.get('notes', '')
        if notes:
            ret.resolution_notes = (ret.resolution_notes or '') + f'\n[{next_status}] {notes}'
        if next_status == 'replacement_sent':
            tracking = request.data.get('tracking_number', '')
            if tracking:
                ret.replacement_tracking = tracking
        ret.status = next_status
        ret.save()
        return Response(ProductReturnSerializer(ret, context={'request': request}).data)


@extend_schema(tags=['quality'])
class VendorProductReturnListView(generics.ListAPIView):
    """Vendeur — retours concernant sa boutique."""
    serializer_class = ProductReturnSerializer
    permission_classes = [IsAuthenticated, IsActiveVendor]
    pagination_class = StandardPagination

    def get_queryset(self):
        store = self.request.user.store
        qs = ProductReturn.objects.filter(
            product__store=store
        ).select_related('requested_by', 'product', 'order_item').prefetch_related('images')
        st = self.request.query_params.get('status')
        if st:
            qs = qs.filter(status=st)
        return qs.order_by('-created_at')


# ── Avis non-conformité fournisseur ───────────────────────────────────────────

@extend_schema(tags=['quality'])
class SupplierQualityNoticeListCreateView(generics.ListCreateAPIView):
    serializer_class = SupplierQualityNoticeSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = SupplierQualityNotice.objects.select_related('supplier', 'inspection')
        supplier_id = self.request.query_params.get('supplier')
        st = self.request.query_params.get('status')
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        if st:
            qs = qs.filter(status=st)
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


@extend_schema(tags=['quality'])
class SupplierQualityNoticeDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = SupplierQualityNoticeSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = SupplierQualityNotice.objects.all()


@extend_schema(tags=['quality'])
class SupplierQualityNoticeSendView(APIView):
    """Envoyer formellement l'avis de non-conformité au fournisseur."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        from django.utils import timezone
        notice = generics.get_object_or_404(SupplierQualityNotice, pk=pk)
        if notice.status != 'draft':
            return Response(
                {'detail': 'Seuls les brouillons peuvent être envoyés.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notice.status = 'sent'
        notice.save(update_fields=['status'])
        # Mise à jour score fournisseur
        from .services import _update_supplier_quality_score
        _update_supplier_quality_score(notice.supplier, notice.quantity_defective)
        return Response(SupplierQualityNoticeSerializer(notice).data)


@extend_schema(tags=['quality'])
class QualityDashboardView(APIView):
    """Tableau de bord qualité pour admin ou vendeur."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.products.models import Product

        if request.user.role == 'admin':
            profiles_qs = ProductQualityProfile.objects.all()
            returns_qs = ProductReturn.objects.all()
            inspections_qs = QualityInspection.objects.all()
            notices_qs = SupplierQualityNotice.objects.filter(status__in=('draft', 'sent'))
        else:
            if not hasattr(request.user, 'store'):
                return Response({'detail': 'Aucune boutique associée.'}, status=403)
            store = request.user.store
            profiles_qs = ProductQualityProfile.objects.filter(product__store=store)
            returns_qs = ProductReturn.objects.filter(product__store=store)
            inspections_qs = QualityInspection.objects.filter(product__store=store)
            notices_qs = SupplierQualityNotice.objects.none()

        return Response({
            'products_grade_A': profiles_qs.filter(grade='A').count(),
            'products_grade_B': profiles_qs.filter(grade='B').count(),
            'products_grade_C': profiles_qs.filter(grade='C').count(),
            'products_grade_D': profiles_qs.filter(grade='D').count(),
            'products_grade_F': profiles_qs.filter(grade='F').count(),
            'pending_returns': returns_qs.filter(status='pending').count(),
            'under_inspection': returns_qs.filter(status='under_inspection').count(),
            'total_inspections': inspections_qs.count(),
            'failed_inspections': inspections_qs.filter(result='failed').count(),
            'open_quality_notices': notices_qs.count(),
        })
