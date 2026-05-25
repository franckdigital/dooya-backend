from django.db.models import F
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsAdmin, IsActiveVendor
from core.pagination import StandardPagination
from .models import (
    Warehouse, StockLocation, StockMovement, StockAlert,
    StockReservation, SupplierOrder, SupplierOrderItem,
)
from .serializers import (
    WarehouseSerializer, StockLocationSerializer, StockMovementSerializer,
    ManualAdjustmentSerializer, StockAlertSerializer,
    SupplierOrderSerializer, SupplierOrderItemSerializer,
    StockDashboardSerializer,
)
from .services import record_movement


# ── Entrepôts ─────────────────────────────────────────────────────────────────

@extend_schema(tags=['inventory'])
class WarehouseListCreateView(generics.ListCreateAPIView):
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Warehouse.objects.all().order_by('-is_default', 'name')


@extend_schema(tags=['inventory'])
class WarehouseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Warehouse.objects.all()


# ── Stock locations ───────────────────────────────────────────────────────────

@extend_schema(tags=['inventory'])
class StockLocationListView(generics.ListAPIView):
    serializer_class = StockLocationSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = StockLocation.objects.select_related(
            'product', 'variant', 'warehouse'
        )
        warehouse = self.request.query_params.get('warehouse')
        product = self.request.query_params.get('product')
        low = self.request.query_params.get('low_stock')
        if warehouse:
            qs = qs.filter(warehouse_id=warehouse)
        if product:
            qs = qs.filter(product_id=product)
        if low:
            from django.db.models import F
            qs = qs.filter(quantity__lte=F('reorder_point'))
        return qs.order_by('warehouse', 'product__name')


@extend_schema(tags=['inventory'])
class VendorStockLocationListView(generics.ListAPIView):
    """Vendeur — stock de ses propres produits."""
    serializer_class = StockLocationSerializer
    permission_classes = [IsAuthenticated, IsActiveVendor]
    pagination_class = StandardPagination

    def get_queryset(self):
        store = self.request.user.store
        qs = StockLocation.objects.filter(
            product__store=store
        ).select_related('product', 'variant', 'warehouse')
        low = self.request.query_params.get('low_stock')
        if low:
            from django.db.models import F
            qs = qs.filter(quantity__lte=F('reorder_point'))
        return qs.order_by('product__name')


# ── Mouvements de stock ───────────────────────────────────────────────────────

@extend_schema(tags=['inventory'])
class StockMovementListView(generics.ListAPIView):
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = StockMovement.objects.select_related('product', 'variant', 'warehouse', 'order')
        for param in ('product', 'reason', 'movement_type', 'warehouse'):
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{f'{param}_id' if param != 'reason' and param != 'movement_type' else param: val})
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs.order_by('-created_at')


@extend_schema(tags=['inventory'])
class VendorStockMovementListView(generics.ListAPIView):
    """Vendeur — historique des mouvements de ses produits."""
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated, IsActiveVendor]
    pagination_class = StandardPagination

    def get_queryset(self):
        store = self.request.user.store
        return StockMovement.objects.filter(
            product__store=store
        ).select_related('product', 'variant', 'warehouse').order_by('-created_at')


@extend_schema(tags=['inventory'])
class ManualStockAdjustmentView(APIView):
    """Admin — ajustement manuel du stock avec traçabilité."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        serializer = ManualAdjustmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        qty = data['quantity']
        movement_type = 'in' if qty > 0 else 'out' if qty < 0 else 'adjustment'

        movement = record_movement(
            product=data['product'],
            quantity=qty,
            reason=data['reason'],
            movement_type=movement_type,
            variant=data.get('variant'),
            warehouse=data.get('warehouse'),
            notes=data.get('notes', ''),
            performed_by=request.user,
        )
        return Response(StockMovementSerializer(movement).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['inventory'])
class VendorManualAdjustmentView(APIView):
    """Vendeur — correction de stock pour ses propres produits."""
    permission_classes = [IsAuthenticated, IsActiveVendor]

    def post(self, request):
        serializer = ManualAdjustmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        product = data['product']
        if product.store != request.user.store:
            return Response(
                {'detail': 'Ce produit ne vous appartient pas.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        qty = data['quantity']
        # Le vendeur ne peut faire que des ajustements, pas des sorties volontaires
        if qty < 0 and data['reason'] not in ('adjustment_negative', 'loss', 'return_supplier'):
            return Response(
                {'detail': 'Raison invalide pour une sortie vendeur.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        movement_type = 'in' if qty > 0 else 'out' if qty < 0 else 'adjustment'
        movement = record_movement(
            product=product,
            quantity=qty,
            reason=data['reason'],
            movement_type=movement_type,
            variant=data.get('variant'),
            notes=data.get('notes', ''),
            performed_by=request.user,
        )
        return Response(StockMovementSerializer(movement).data, status=status.HTTP_201_CREATED)


# ── Alertes stock ─────────────────────────────────────────────────────────────

@extend_schema(tags=['inventory'])
class StockAlertListView(generics.ListAPIView):
    serializer_class = StockAlertSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = StockAlert.objects.select_related('product', 'variant', 'warehouse')
        st = self.request.query_params.get('status', 'active')
        if st:
            qs = qs.filter(status=st)
        return qs.order_by('-created_at')


@extend_schema(tags=['inventory'])
class VendorStockAlertListView(generics.ListAPIView):
    """Vendeur — alertes de ses produits."""
    serializer_class = StockAlertSerializer
    permission_classes = [IsAuthenticated, IsActiveVendor]

    def get_queryset(self):
        store = self.request.user.store
        return StockAlert.objects.filter(
            product__store=store, status='active'
        ).select_related('product', 'variant').order_by('-created_at')


@extend_schema(tags=['inventory'])
class StockAlertAcknowledgeView(APIView):
    """Marquer une alerte comme prise en compte."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        qs = StockAlert.objects.all()
        if request.user.role != 'admin':
            if not hasattr(request.user, 'store'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied()
            qs = qs.filter(product__store=request.user.store)

        alert = generics.get_object_or_404(qs, pk=pk)
        alert.status = 'acknowledged'
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save(update_fields=['status', 'acknowledged_by', 'acknowledged_at'])
        return Response({'detail': 'Alerte prise en compte.'})


# ── Commandes fournisseurs ────────────────────────────────────────────────────

@extend_schema(tags=['inventory'])
class SupplierOrderListCreateView(generics.ListCreateAPIView):
    serializer_class = SupplierOrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        if self.request.user.role == 'admin':
            qs = SupplierOrder.objects.all()
        else:
            qs = SupplierOrder.objects.filter(store=self.request.user.store)
        st = self.request.query_params.get('status')
        if st:
            qs = qs.filter(status=st)
        return qs.select_related('store', 'warehouse').prefetch_related('items').order_by('-created_at')

    def perform_create(self, serializer):
        import random, string
        ref = 'PO' + ''.join(random.choices(string.digits, k=8))
        while SupplierOrder.objects.filter(reference=ref).exists():
            ref = 'PO' + ''.join(random.choices(string.digits, k=8))
        if self.request.user.role != 'admin':
            serializer.save(reference=ref, store=self.request.user.store)
        else:
            serializer.save(reference=ref)


@extend_schema(tags=['inventory'])
class SupplierOrderDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = SupplierOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return SupplierOrder.objects.all()
        return SupplierOrder.objects.filter(store=self.request.user.store)


@extend_schema(tags=['inventory'])
class SupplierOrderReceiveView(APIView):
    """Enregistrer la réception (partielle ou totale) d'une commande fournisseur."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role == 'admin':
            order = generics.get_object_or_404(SupplierOrder, pk=pk)
        else:
            order = generics.get_object_or_404(
                SupplierOrder, pk=pk, store=request.user.store
            )

        if order.status in ('completed', 'cancelled'):
            return Response(
                {'detail': 'Cette commande est déjà clôturée.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items_data = request.data.get('items', [])
        if not items_data:
            return Response({'detail': 'Aucun article fourni.'}, status=status.HTTP_400_BAD_REQUEST)

        for item_data in items_data:
            try:
                item = order.items.get(pk=item_data['id'])
            except SupplierOrderItem.DoesNotExist:
                continue

            qty_received = int(item_data.get('quantity_received', 0))
            if qty_received <= 0:
                continue

            item.quantity_received += qty_received
            item.is_fully_received = item.quantity_received >= item.quantity_ordered
            item.save(update_fields=['quantity_received', 'is_fully_received'])

            # Entrée en stock
            record_movement(
                product=item.product,
                quantity=qty_received,
                reason='purchase',
                movement_type='in',
                variant=item.variant,
                warehouse=order.warehouse,
                reference=order.reference,
                notes=f'Réception commande fournisseur {order.reference}',
                performed_by=request.user,
            )

        # Mettre à jour le statut de la commande
        all_items = order.items.all()
        if all(i.is_fully_received for i in all_items):
            order.status = 'completed'
            order.received_date = timezone.now().date()
        else:
            order.status = 'partial'
        order.save(update_fields=['status', 'received_date'])

        return Response(SupplierOrderSerializer(order).data)


# ── Dashboard stock ───────────────────────────────────────────────────────────

@extend_schema(tags=['inventory'])
class StockDashboardView(APIView):
    """Tableau de bord stock pour admin ou vendeur."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.products.models import Product
        from django.db.models import Count

        today = timezone.now().date()

        if request.user.role == 'admin':
            products_qs = Product.objects.filter(is_active=True)
            alerts_qs = StockAlert.objects.filter(status='active')
            movements_qs = StockMovement.objects.filter(created_at__date=today)
            supplier_qs = SupplierOrder.objects.filter(status__in=('draft', 'sent', 'confirmed'))
        else:
            if not hasattr(request.user, 'store'):
                return Response({'detail': 'Aucune boutique associée.'}, status=403)
            store = request.user.store
            products_qs = Product.objects.filter(store=store, is_active=True)
            alerts_qs = StockAlert.objects.filter(product__store=store, status='active')
            movements_qs = StockMovement.objects.filter(
                product__store=store, created_at__date=today
            )
            supplier_qs = SupplierOrder.objects.filter(
                store=store, status__in=('draft', 'sent', 'confirmed')
            )

        warehouses_count = Warehouse.objects.filter(is_active=True).count() if request.user.role == 'admin' else 0
        data = {
            'total_products': products_qs.count(),
            'out_of_stock': products_qs.filter(stock=0).count(),
            'low_stock': products_qs.filter(
                stock__gt=0, stock__lte=F('min_stock_alert')
            ).count(),
            'active_alerts': alerts_qs.count(),
            'total_movements_today': movements_qs.count(),
            'pending_supplier_orders': supplier_qs.count(),
            'warehouses_count': warehouses_count,
        }
        return Response(data)
