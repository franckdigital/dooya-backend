from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsVendor, IsAdmin
from core.pagination import StandardPagination
from .models import Order, OrderItem, OrderStatusHistory, Invoice
from .serializers import (
    OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer,
    OrderStatusUpdateSerializer,
)


@extend_schema(tags=['orders'])
class OrderListView(generics.ListAPIView):
    serializer_class = OrderListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Order.objects.filter(user=self.request.user).prefetch_related('items')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by('-created_at')


@extend_schema(tags=['orders'])
class OrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            order = serializer.save()
            try:
                from .tasks import send_order_confirmation
                send_order_confirmation.delay(order.pk)
            except Exception:
                pass
            return Response(OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['orders'])
class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'order_number'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items', 'status_history')


@extend_schema(tags=['orders'])
class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_number):
        try:
            order = Order.objects.get(order_number=order_number, user=request.user)
        except Order.DoesNotExist:
            return Response({'detail': 'Commande introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if order.status not in ('pending', 'confirmed'):
            return Response({'detail': 'Cette commande ne peut plus être annulée.'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'cancelled'
        order.save(update_fields=['status'])
        OrderStatusHistory.objects.create(order=order, status='cancelled', created_by=request.user)
        for item in order.items.all():
            if item.variant:
                from apps.products.models import ProductVariant
                ProductVariant.objects.filter(pk=item.variant.pk).update(stock=item.variant.stock + item.quantity)
            else:
                from apps.products.models import Product
                Product.objects.filter(pk=item.product.pk).update(stock=item.product.stock + item.quantity)
        return Response({'detail': 'Commande annulée.'})


@extend_schema(tags=['orders'])
class VendorOrderListView(generics.ListAPIView):
    serializer_class = OrderListSerializer
    permission_classes = [IsAuthenticated, IsVendor]
    pagination_class = StandardPagination

    def get_queryset(self):
        store = self.request.user.store
        order_ids = OrderItem.objects.filter(store=store).values_list('order_id', flat=True).distinct()
        qs = Order.objects.filter(pk__in=order_ids).prefetch_related('items')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by('-created_at')


@extend_schema(tags=['orders'])
class VendorOrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAuthenticated, IsVendor]
    lookup_field = 'order_number'

    def get_queryset(self):
        store = self.request.user.store
        order_ids = OrderItem.objects.filter(store=store).values_list('order_id', flat=True).distinct()
        return Order.objects.filter(pk__in=order_ids).prefetch_related('items', 'status_history')


@extend_schema(tags=['orders'])
class VendorOrderUpdateStatusView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request, order_number):
        store = request.user.store
        order_ids = OrderItem.objects.filter(store=store).values_list('order_id', flat=True).distinct()
        try:
            order = Order.objects.get(order_number=order_number, pk__in=order_ids)
        except Order.DoesNotExist:
            return Response({'detail': 'Commande introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrderStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        allowed = ('confirmed', 'processing', 'shipped')
        new_status = serializer.validated_data['status']
        if new_status not in allowed:
            return Response({'detail': f'Statut non autorisé pour le vendeur: {new_status}'}, status=status.HTTP_403_FORBIDDEN)
        order.status = new_status
        order.save(update_fields=['status'])
        OrderStatusHistory.objects.create(order=order, status=new_status, note=serializer.validated_data.get('note', ''), created_by=request.user)
        return Response(OrderDetailSerializer(order).data)


@extend_schema(tags=['orders'])
class AdminOrderListView(generics.ListAPIView):
    serializer_class = OrderListSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Order.objects.all().prefetch_related('items')
        status_filter = self.request.query_params.get('status')
        payment_status = self.request.query_params.get('payment_status')
        search = self.request.query_params.get('search')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if payment_status:
            qs = qs.filter(payment_status=payment_status)
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(order_number__icontains=search) |
                Q(user__email__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)
            )
        return qs.order_by('-created_at')


@extend_schema(tags=['orders'])
class AdminOrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    lookup_field = 'order_number'
    queryset = Order.objects.all().prefetch_related('items', 'status_history')


@extend_schema(tags=['orders'])
class AdminOrderUpdateStatusView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, order_number):
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return Response({'detail': 'Commande introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrderStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        new_status = serializer.validated_data.get('status')
        new_payment_status = serializer.validated_data.get('payment_status')
        update_fields = []
        if new_status:
            order.status = new_status
            update_fields.append('status')
            if new_status in ('delivered', 'completed') and order.payment_status != 'paid' and not new_payment_status:
                order.payment_status = 'paid'
                update_fields.append('payment_status')
        if new_payment_status:
            order.payment_status = new_payment_status
            if 'payment_status' not in update_fields:
                update_fields.append('payment_status')
        if update_fields:
            order.save(update_fields=update_fields)
        if new_status:
            OrderStatusHistory.objects.create(order=order, status=order.status, note=serializer.validated_data.get('note', ''), created_by=request.user)

        # Auto-create delivery record when order is confirmed
        if new_status and order.status == 'confirmed':
            try:
                from apps.deliveries.models import Delivery, RelayPoint
                if not Delivery.objects.filter(order=order).exists():
                    addr = order.shipping_address or {}
                    relay_name = addr.get('relay_name')
                    relay_point = RelayPoint.objects.filter(name=relay_name).first() if relay_name else None
                    Delivery.objects.create(
                        order=order,
                        type='relay_point' if relay_name else 'home_delivery',
                        status='pending',
                        delivery_address=addr,
                        relay_point=relay_point,
                    )
            except Exception:
                pass

        return Response(OrderDetailSerializer(order).data)


@extend_schema(tags=['orders'])
class InvoiceDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_number):
        try:
            order = Order.objects.get(order_number=order_number, user=request.user)
        except Order.DoesNotExist:
            if request.user.role == 'admin':
                try:
                    order = Order.objects.get(order_number=order_number)
                except Order.DoesNotExist:
                    return Response({'detail': 'Commande introuvable.'}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({'detail': 'Commande introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        # Generate PDF bytes directly (no file read-after-write issue)
        try:
            pdf_bytes = self._build_pdf(order)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f'Invoice build error: {e}')
            return Response({'detail': f'Impossible de générer la facture : {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Persist invoice record + file (best-effort, don't block download on failure)
        try:
            from django.core.files.base import ContentFile
            invoice_number = f'INV-{order.order_number}'
            invoice, _ = Invoice.objects.get_or_create(
                order=order, defaults={'invoice_number': invoice_number}
            )
            if not invoice.invoice_number:
                invoice.invoice_number = invoice_number
            invoice.pdf_file.save(f'{invoice_number}.pdf', ContentFile(pdf_bytes), save=True)
        except Exception:
            pass

        from django.http import HttpResponse
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="facture-{order.order_number}.pdf"'
        response['Content-Length'] = len(pdf_bytes)
        return response

    @staticmethod
    def _build_pdf(order):
        """Generate PDF bytes and return them directly without file I/O."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        import io

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        c.setFont('Helvetica-Bold', 24)
        c.drawString(20 * mm, height - 25 * mm, 'DOOYA')
        c.setFont('Helvetica', 11)
        c.drawString(20 * mm, height - 33 * mm, "L'expert Ivoirien de la Literie")
        c.setFont('Helvetica-Bold', 16)
        c.drawString(20 * mm, height - 50 * mm, f'FACTURE #{order.order_number}')
        c.setFont('Helvetica', 11)
        c.drawString(20 * mm, height - 58 * mm, f'Date : {order.created_at.strftime("%d/%m/%Y")}')

        user = order.user
        if user:
            full_name = user.get_full_name() or user.email
            c.setFont('Helvetica-Bold', 12)
            c.drawString(20 * mm, height - 75 * mm, 'Client :')
            c.setFont('Helvetica', 11)
            c.drawString(20 * mm, height - 83 * mm, full_name)
            c.drawString(20 * mm, height - 90 * mm, user.email)
            if getattr(user, 'phone', None):
                c.drawString(20 * mm, height - 97 * mm, user.phone)

        addr = order.shipping_address or {}
        if addr:
            c.setFont('Helvetica-Bold', 12)
            c.drawString(110 * mm, height - 75 * mm, 'Livraison :')
            c.setFont('Helvetica', 11)
            for i, val in enumerate([
                addr.get('full_name', ''),
                addr.get('street', addr.get('street_address', '')),
                addr.get('city', ''),
                addr.get('phone', ''),
            ]):
                if val:
                    c.drawString(110 * mm, height - (83 + i * 7) * mm, val)

        y = height - 120 * mm
        c.setFillColorRGB(0.95, 0.95, 0.95)
        c.rect(15 * mm, y - 2 * mm, 180 * mm, 8 * mm, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.setFont('Helvetica-Bold', 10)
        c.drawString(17 * mm, y + 2 * mm, 'Produit')
        c.drawString(110 * mm, y + 2 * mm, 'Qté')
        c.drawString(130 * mm, y + 2 * mm, 'Prix unitaire')
        c.drawString(165 * mm, y + 2 * mm, 'Total')
        y -= 10 * mm
        c.setFont('Helvetica', 10)
        for item in order.items.all():
            c.drawString(17 * mm, y, item.product_name[:50])
            c.drawString(110 * mm, y, str(item.quantity))
            c.drawString(130 * mm, y, f'{int(item.unit_price):,} F CFA')
            c.drawString(165 * mm, y, f'{int(item.total_price):,} F CFA')
            y -= 7 * mm

        y -= 5 * mm
        c.line(15 * mm, y + 3 * mm, 195 * mm, y + 3 * mm)
        c.setFont('Helvetica', 10)
        c.drawString(130 * mm, y - 2 * mm, 'Sous-total :')
        c.drawString(165 * mm, y - 2 * mm, f'{int(order.subtotal):,} F CFA')
        y -= 7 * mm
        if order.shipping_cost:
            c.drawString(130 * mm, y - 2 * mm, 'Livraison :')
            c.drawString(165 * mm, y - 2 * mm, f'{int(order.shipping_cost):,} F CFA')
            y -= 7 * mm
        if order.discount:
            c.drawString(130 * mm, y - 2 * mm, 'Remise :')
            c.drawString(165 * mm, y - 2 * mm, f'-{int(order.discount):,} F CFA')
            y -= 7 * mm
        c.setFont('Helvetica-Bold', 12)
        c.drawString(130 * mm, y - 2 * mm, 'TOTAL :')
        c.drawString(165 * mm, y - 2 * mm, f'{int(order.total_amount):,} F CFA')

        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer.read()

    @staticmethod
    def _build_invoice(order):
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        import io
        from django.core.files.base import ContentFile

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # En-tête
        c.setFont('Helvetica-Bold', 24)
        c.drawString(20 * mm, height - 25 * mm, 'DOOYA')
        c.setFont('Helvetica', 11)
        c.drawString(20 * mm, height - 33 * mm, "L'expert Ivoirien de la Literie")
        c.setFont('Helvetica-Bold', 16)
        c.drawString(20 * mm, height - 50 * mm, f'FACTURE #{order.order_number}')
        c.setFont('Helvetica', 11)
        c.drawString(20 * mm, height - 58 * mm, f'Date : {order.created_at.strftime("%d/%m/%Y")}')
        c.drawString(20 * mm, height - 65 * mm, f'Statut paiement : {order.get_payment_status_display() if hasattr(order, "get_payment_status_display") else order.payment_status}')

        # Client
        user = order.user
        if user:
            full_name = user.get_full_name() or user.email
            c.setFont('Helvetica-Bold', 12)
            c.drawString(20 * mm, height - 80 * mm, 'Client :')
            c.setFont('Helvetica', 11)
            c.drawString(20 * mm, height - 88 * mm, full_name)
            c.drawString(20 * mm, height - 95 * mm, user.email)
            if getattr(user, 'phone', None):
                c.drawString(20 * mm, height - 102 * mm, user.phone)

        # Adresse de livraison
        addr = order.shipping_address or {}
        if addr:
            c.setFont('Helvetica-Bold', 12)
            c.drawString(110 * mm, height - 80 * mm, 'Livraison :')
            c.setFont('Helvetica', 11)
            c.drawString(110 * mm, height - 88 * mm, addr.get('full_name', ''))
            c.drawString(110 * mm, height - 95 * mm, addr.get('street', addr.get('street_address', '')))
            c.drawString(110 * mm, height - 102 * mm, addr.get('city', ''))
            if addr.get('phone'):
                c.drawString(110 * mm, height - 109 * mm, addr['phone'])

        # Tableau articles
        y = height - 125 * mm
        c.setFillColorRGB(0.95, 0.95, 0.95)
        c.rect(15 * mm, y - 2 * mm, 180 * mm, 8 * mm, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.setFont('Helvetica-Bold', 10)
        c.drawString(17 * mm, y + 2 * mm, 'Produit')
        c.drawString(110 * mm, y + 2 * mm, 'Qté')
        c.drawString(130 * mm, y + 2 * mm, 'Prix unitaire')
        c.drawString(165 * mm, y + 2 * mm, 'Total')
        y -= 10 * mm
        c.setFont('Helvetica', 10)
        for item in order.items.all():
            c.drawString(17 * mm, y, item.product_name[:50])
            c.drawString(110 * mm, y, str(item.quantity))
            c.drawString(130 * mm, y, f'{int(item.unit_price):,} F CFA')
            c.drawString(165 * mm, y, f'{int(item.total_price):,} F CFA')
            y -= 7 * mm

        # Totaux
        y -= 5 * mm
        c.line(15 * mm, y + 3 * mm, 195 * mm, y + 3 * mm)
        c.setFont('Helvetica', 10)
        c.drawString(130 * mm, y - 2 * mm, 'Sous-total :')
        c.drawString(165 * mm, y - 2 * mm, f'{int(order.subtotal):,} F CFA')
        y -= 7 * mm
        if order.shipping_cost:
            c.drawString(130 * mm, y - 2 * mm, 'Livraison :')
            c.drawString(165 * mm, y - 2 * mm, f'{int(order.shipping_cost):,} F CFA')
            y -= 7 * mm
        if order.discount:
            c.drawString(130 * mm, y - 2 * mm, 'Remise :')
            c.drawString(165 * mm, y - 2 * mm, f'-{int(order.discount):,} F CFA')
            y -= 7 * mm
        c.setFont('Helvetica-Bold', 12)
        c.drawString(130 * mm, y - 2 * mm, 'TOTAL :')
        c.drawString(165 * mm, y - 2 * mm, f'{int(order.total_amount):,} F CFA')

        c.showPage()
        c.save()
        buffer.seek(0)
        pdf_bytes = buffer.read()

        invoice_number = f'INV-{order.order_number}'
        invoice, _ = Invoice.objects.get_or_create(
            order=order, defaults={'invoice_number': invoice_number}
        )
        if not invoice.invoice_number:
            invoice.invoice_number = invoice_number
        invoice.pdf_file.save(f'{invoice_number}.pdf', ContentFile(pdf_bytes), save=True)
        return invoice
