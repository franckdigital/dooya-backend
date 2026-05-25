from celery import shared_task


@shared_task(name='inventory.release_expired_reservations')
def release_expired_reservations_task():
    """Libère les réservations de stock expirées. Exécuté toutes les 5 minutes."""
    from .services import release_expired_reservations
    count = release_expired_reservations()
    return f'{count} réservation(s) expirée(s) libérée(s).'


@shared_task(name='inventory.check_low_stock')
def check_low_stock_task():
    """
    Vérifie tous les produits actifs et crée des alertes si le stock
    est bas ou épuisé. Exécuté toutes les heures.
    """
    from apps.products.models import Product
    from .services import _check_and_create_alerts

    products = Product.objects.filter(is_active=True).select_related('store')
    count = 0
    for product in products:
        if product.stock <= product.min_stock_alert:
            _check_and_create_alerts(product, None, product.stock)
            count += 1
    return f'{count} produit(s) avec stock bas détecté(s).'


@shared_task(name='inventory.auto_create_supplier_orders')
def auto_create_supplier_orders_task():
    """
    Crée automatiquement des commandes fournisseurs brouillon pour les
    emplacements stock en dessous du reorder_point. Exécuté chaque nuit.
    """
    from django.db.models import F
    from .models import StockLocation, SupplierOrder, SupplierOrderItem
    import random
    import string

    locations = StockLocation.objects.filter(
        quantity__lte=F('reorder_point'),
        warehouse__is_active=True,
    ).select_related('product', 'product__store', 'variant', 'warehouse')

    created = 0
    for loc in locations:
        store = loc.product.store
        ref = 'PO' + ''.join(random.choices(string.digits, k=8))
        while SupplierOrder.objects.filter(reference=ref).exists():
            ref = 'PO' + ''.join(random.choices(string.digits, k=8))
        order = SupplierOrder.objects.create(
            reference=ref,
            store=store,
            warehouse=loc.warehouse,
            supplier_name='Fournisseur par défaut',
            status='draft',
            notes=f'Réapprovisionnement automatique — stock: {loc.quantity}',
        )
        SupplierOrderItem.objects.create(
            supplier_order=order,
            product=loc.product,
            variant=loc.variant,
            quantity_ordered=loc.reorder_quantity,
            unit_cost=loc.product.cost_price or 0,
        )
        try:
            from apps.notifications.models import Notification
            Notification.objects.create(
                user=store.owner,
                type='system',
                title='Commande fournisseur créée',
                body=(
                    f'Une commande fournisseur ({ref}) a été créée automatiquement '
                    f'pour "{loc.product.name}" (stock: {loc.quantity}).'
                ),
                data={'supplier_order_ref': ref},
            )
        except Exception:
            pass
        created += 1

    return f'{created} commande(s) fournisseur créée(s) automatiquement.'
