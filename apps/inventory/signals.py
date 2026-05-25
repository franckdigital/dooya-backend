from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='orders.Order')
def handle_order_status_change(sender, instance, created, **kwargs):
    """
    - confirmed  → décrémenter le stock
    - cancelled/refunded → réincrémenter le stock
    """
    if created:
        return

    previous_status = getattr(instance, '_previous_status', None)
    if previous_status == instance.status:
        return

    if instance.status == 'confirmed' and previous_status not in ('confirmed',):
        _decrement_stock_for_order(instance)

    elif instance.status in ('cancelled', 'refunded') and previous_status in (
        'confirmed', 'processing', 'shipped'
    ):
        _restore_stock_for_order(instance)


def _decrement_stock_for_order(order):
    try:
        from apps.inventory.services import record_movement
        for item in order.items.select_related('product', 'variant').all():
            record_movement(
                product=item.product,
                quantity=-item.quantity,
                reason='sale',
                movement_type='out',
                variant=item.variant,
                order=order,
                reference=order.order_number,
                notes=f'Vente commande {order.order_number}',
            )
    except Exception:
        pass


def _restore_stock_for_order(order):
    try:
        from apps.inventory.services import record_movement
        for item in order.items.select_related('product', 'variant').all():
            record_movement(
                product=item.product,
                quantity=item.quantity,
                reason='cancelled_order',
                movement_type='in',
                variant=item.variant,
                order=order,
                reference=order.order_number,
                notes=f'Annulation/remboursement commande {order.order_number}',
            )
    except Exception:
        pass


# Capturer le statut précédent avant la sauvegarde
from django.db.models.signals import pre_save

@receiver(pre_save, sender='orders.Order')
def capture_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._previous_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None
