"""
Service layer pour les opérations de stock atomiques.
Toujours appeler ces fonctions dans une transaction pour garantir la cohérence.
"""
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone


def _get_or_create_default_warehouse():
    from .models import Warehouse
    wh = Warehouse.objects.filter(is_default=True, is_active=True).first()
    if not wh:
        wh = Warehouse.objects.filter(is_active=True).first()
    return wh


def record_movement(product, quantity, reason, movement_type,
                    variant=None, warehouse=None, order=None,
                    reference='', notes='', performed_by=None):
    """
    Enregistre un mouvement de stock et met à jour Product.stock / Variant.stock.
    quantity: positif = entrée, négatif = sortie.
    """
    from .models import StockMovement
    from apps.products.models import Product, ProductVariant

    with transaction.atomic():
        if variant:
            obj = ProductVariant.objects.select_for_update().get(pk=variant.pk)
            stock_before = obj.stock
            obj.stock = max(0, obj.stock + quantity)
            obj.save(update_fields=['stock'])
            stock_after = obj.stock
            # Synchroniser le stock agrégé du produit
            product_obj = Product.objects.select_for_update().get(pk=product.pk)
            product_obj.stock = product_obj.variants.aggregate(total=Sum('stock'))['total'] or 0
            product_obj.save(update_fields=['stock'])
        else:
            obj = Product.objects.select_for_update().get(pk=product.pk)
            stock_before = obj.stock
            obj.stock = max(0, obj.stock + quantity)
            obj.save(update_fields=['stock'])
            stock_after = obj.stock

        if warehouse is None:
            warehouse = _get_or_create_default_warehouse()

        # Mettre à jour StockLocation
        if warehouse:
            from .models import StockLocation
            loc, _ = StockLocation.objects.get_or_create(
                warehouse=warehouse, product=product, variant=variant,
                defaults={'quantity': 0}
            )
            loc.quantity = max(0, loc.quantity + quantity)
            loc.save(update_fields=['quantity'])

        movement = StockMovement.objects.create(
            product=product,
            variant=variant,
            warehouse=warehouse,
            movement_type=movement_type,
            reason=reason,
            quantity=quantity,
            stock_before=stock_before,
            stock_after=stock_after,
            reference=reference,
            order=order,
            performed_by=performed_by,
            notes=notes,
        )

    _check_and_create_alerts(product, variant, stock_after)
    return movement


def _check_and_create_alerts(product, variant, current_stock):
    """Crée une alerte si le stock passe sous le seuil min."""
    from .models import StockAlert
    threshold = product.min_stock_alert

    if current_stock == 0:
        alert_type = 'out_of_stock'
        msg = f'Rupture de stock pour "{product.name}"'
    elif current_stock <= threshold:
        alert_type = 'low_stock'
        msg = f'Stock bas pour "{product.name}": {current_stock} unité(s) restante(s)'
    else:
        # Résoudre les alertes actives si le stock est redevenu correct
        StockAlert.objects.filter(
            product=product, variant=variant, status='active'
        ).update(status='resolved')
        return

    # Ne pas créer de doublon si une alerte active existe déjà
    exists = StockAlert.objects.filter(
        product=product, variant=variant,
        alert_type=alert_type, status='active',
    ).exists()
    if not exists:
        StockAlert.objects.create(
            product=product,
            variant=variant,
            alert_type=alert_type,
            current_stock=current_stock,
            threshold=threshold,
            message=msg,
        )
        # Notifier le vendeur
        _notify_vendor_low_stock(product, current_stock, alert_type)


def _notify_vendor_low_stock(product, current_stock, alert_type):
    try:
        from apps.notifications.models import Notification
        vendor_user = product.store.owner
        title = 'Rupture de stock' if alert_type == 'out_of_stock' else 'Stock bas'
        body = (
            f'Votre produit "{product.name}" est en rupture de stock.'
            if alert_type == 'out_of_stock'
            else f'Stock bas pour "{product.name}": {current_stock} unité(s) restante(s).'
        )
        Notification.objects.create(
            user=vendor_user,
            type='system',
            title=title,
            body=body,
            data={'product_id': product.id, 'stock': current_stock},
        )
    except Exception:
        pass


def reserve_stock(product, quantity, variant=None, order=None,
                  session_key='', minutes=30):
    """
    Réserve du stock pour une commande ou un panier.
    Retourne la réservation ou lève une exception si stock insuffisant.
    """
    from .models import StockReservation
    from rest_framework.exceptions import ValidationError

    with transaction.atomic():
        from apps.products.models import Product as P, ProductVariant as PV
        if variant:
            obj = PV.objects.select_for_update().get(pk=variant.pk)
        else:
            obj = P.objects.select_for_update().get(pk=product.pk)

        if obj.stock < quantity:
            raise ValidationError(
                f'Stock insuffisant pour "{product.name}". '
                f'Disponible: {obj.stock}, demandé: {quantity}.'
            )

        reservation = StockReservation.objects.create(
            product=product,
            variant=variant,
            order=order,
            session_key=session_key or '',
            quantity=quantity,
            expires_at=timezone.now() + timezone.timedelta(minutes=minutes),
        )

    return reservation


def confirm_reservation(reservation):
    """Confirme une réservation : marque comme confirmée et décrémente le stock."""
    with transaction.atomic():
        if reservation.is_confirmed:
            return
        if reservation.is_expired:
            reservation.delete()
            raise ValueError('La réservation a expiré.')

        record_movement(
            product=reservation.product,
            quantity=-reservation.quantity,
            reason='sale',
            movement_type='out',
            variant=reservation.variant,
            order=reservation.order,
            reference=reservation.order.order_number if reservation.order else '',
        )
        reservation.is_confirmed = True
        reservation.save(update_fields=['is_confirmed'])


def release_reservation(reservation):
    """Libère une réservation sans décrémenter le stock."""
    reservation.delete()


def release_expired_reservations():
    """Libère toutes les réservations expirées (appelé par Celery beat)."""
    from .models import StockReservation
    expired = StockReservation.objects.filter(
        is_confirmed=False,
        expires_at__lt=timezone.now(),
    )
    count = expired.count()
    expired.delete()
    return count
