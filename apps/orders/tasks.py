import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_invoice_pdf(self, order_id):
    try:
        from apps.orders.models import Order, Invoice
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
        import io
        from django.core.files.base import ContentFile

        order = Order.objects.get(pk=order_id)
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        c.setFont('Helvetica-Bold', 24)
        c.drawString(20 * mm, height - 30 * mm, 'DOOYA')
        c.setFont('Helvetica', 12)
        c.drawString(20 * mm, height - 40 * mm, 'Plateforme E-commerce')

        c.setFont('Helvetica-Bold', 16)
        c.drawString(20 * mm, height - 60 * mm, f'FACTURE #{order.order_number}')
        c.setFont('Helvetica', 11)
        c.drawString(20 * mm, height - 70 * mm, f'Date: {order.created_at.strftime("%d/%m/%Y")}')

        addr = order.shipping_address
        c.setFont('Helvetica-Bold', 12)
        c.drawString(20 * mm, height - 90 * mm, 'Adresse de livraison:')
        c.setFont('Helvetica', 11)
        c.drawString(20 * mm, height - 100 * mm, addr.get('full_name', ''))
        c.drawString(20 * mm, height - 108 * mm, addr.get('street', ''))
        c.drawString(20 * mm, height - 116 * mm, f"{addr.get('city', '')}, {addr.get('country', '')}")

        y = height - 140 * mm
        c.setFont('Helvetica-Bold', 11)
        c.drawString(20 * mm, y, 'Produit')
        c.drawString(100 * mm, y, 'Qté')
        c.drawString(130 * mm, y, 'Prix unitaire')
        c.drawString(165 * mm, y, 'Total')
        y -= 8 * mm

        c.setFont('Helvetica', 10)
        for item in order.items.all():
            c.drawString(20 * mm, y, item.product_name[:40])
            c.drawString(100 * mm, y, str(item.quantity))
            c.drawString(130 * mm, y, f'{int(item.unit_price):,} XOF')
            c.drawString(165 * mm, y, f'{int(item.total_price):,} XOF')
            y -= 7 * mm

        y -= 5 * mm
        c.setFont('Helvetica-Bold', 11)
        c.drawString(130 * mm, y, 'Sous-total:')
        c.drawString(165 * mm, y, f'{int(order.subtotal):,} XOF')
        y -= 7 * mm
        if order.shipping_cost:
            c.drawString(130 * mm, y, 'Livraison:')
            c.drawString(165 * mm, y, f'{int(order.shipping_cost):,} XOF')
            y -= 7 * mm
        if order.discount:
            c.drawString(130 * mm, y, 'Remise:')
            c.drawString(165 * mm, y, f'-{int(order.discount):,} XOF')
            y -= 7 * mm
        c.setFont('Helvetica-Bold', 13)
        c.drawString(130 * mm, y, 'TOTAL:')
        c.drawString(165 * mm, y, f'{int(order.total_amount):,} XOF')

        c.showPage()
        c.save()
        buffer.seek(0)
        pdf_content = buffer.read()

        invoice_number = f'INV-{order.order_number}'
        invoice, _ = Invoice.objects.get_or_create(order=order, defaults={'invoice_number': invoice_number})
        invoice.pdf_file.save(f'{invoice_number}.pdf', ContentFile(pdf_content), save=True)
        return {'status': 'success', 'invoice_number': invoice.invoice_number}
    except Exception as exc:
        logger.error(f"Invoice generation error for order {order_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_order_confirmation(self, order_id):
    try:
        from apps.orders.models import Order
        from apps.notifications.services import notify

        order = Order.objects.select_related('user').get(pk=order_id)
        notify(
            user=order.user,
            notification_type='order',
            title='Commande confirmée',
            body=f'Votre commande #{order.order_number} a été reçue et est en cours de traitement.',
            data={'order_number': order.order_number, 'order_id': order.pk},
            channels=['in_app', 'email', 'whatsapp'],
        )
        return {'status': 'sent', 'order_number': order.order_number}
    except Exception as exc:
        logger.error(f"Order confirmation error for {order_id}: {exc}")
        raise self.retry(exc=exc, countdown=30)


@shared_task
def cancel_unpaid_orders():
    from apps.orders.models import Order, OrderStatusHistory
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(hours=24)
    unpaid_orders = Order.objects.filter(
        status='pending',
        payment_status='pending',
        created_at__lt=cutoff,
    )
    cancelled_count = 0
    for order in unpaid_orders:
        order.status = 'cancelled'
        order.save(update_fields=['status'])
        OrderStatusHistory.objects.create(
            order=order,
            status='cancelled',
            note='Annulation automatique après 24h sans paiement.',
        )
        for item in order.items.all():
            if item.variant:
                from apps.products.models import ProductVariant
                ProductVariant.objects.filter(pk=item.variant_id).update(stock=item.variant.stock + item.quantity)
            else:
                from apps.products.models import Product
                Product.objects.filter(pk=item.product_id).update(stock=item.product.stock + item.quantity)
        cancelled_count += 1
    logger.info(f"Cancelled {cancelled_count} unpaid orders.")
    return cancelled_count
