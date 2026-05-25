from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='orders.Order')
def notify_live_order(sender, instance, created, **kwargs):
    """Diffuse un événement WebSocket quand une commande est passée pendant un live."""
    if not created:
        return

    from .models import LiveOrder, LiveSession
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    live_order = LiveOrder.objects.filter(order=instance).select_related(
        'session', 'live_product__product'
    ).first()
    if not live_order:
        return

    session = live_order.session
    if session.status != 'live':
        return

    # Mettre à jour les stats
    LiveSession.objects.filter(pk=session.pk).update(
        total_orders=session.total_orders + 1,
        total_revenue=session.total_revenue + instance.total_amount,
    )
    if live_order.live_product:
        from .models import LiveProduct
        LiveProduct.objects.filter(pk=live_order.live_product.pk).update(
            units_sold=live_order.live_product.units_sold + 1
        )

    channel_layer = get_channel_layer()
    if channel_layer:
        product_name = live_order.live_product.product.name if live_order.live_product else ''
        user_name = instance.user.get_full_name() if instance.user else 'Un client'
        async_to_sync(channel_layer.group_send)(
            f'live_{session.room_id}',
            {
                'type': 'order_placed_event',
                'order_data': {
                    'order_number': instance.order_number,
                    'product_name': product_name,
                    'user_name': user_name,
                }
            }
        )
