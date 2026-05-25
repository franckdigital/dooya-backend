"""
Services de commission : calcul, confirmation, reversement.
"""
from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

DEFAULT_COMMISSION_RATE = 0.10  # 10% par défaut


def _get_applicable_rule(store, category=None):
    """
    Résout la règle de commission applicable selon la priorité :
    boutique > catégorie > défaut (10%).
    """
    from .models import CommissionRule

    # 1. Règle spécifique à la boutique
    rule = CommissionRule.objects.filter(store=store, is_active=True).first()
    if rule:
        return rule

    # 2. Règle de catégorie
    if category:
        rule = CommissionRule.objects.filter(category=category, is_active=True).first()
        if rule:
            return rule

    return None


def calculate_commission(order) -> dict:
    """
    Calcule la commission pour une commande.
    Retourne un dict avec rate, commission_amount, vendor_amount.
    """
    store = order.items.first().product.store if order.items.exists() else None
    if not store:
        return {'rate': DEFAULT_COMMISSION_RATE, 'commission_amount': 0, 'vendor_amount': order.total_amount, 'rule': None}

    category = order.items.first().product.category if order.items.exists() else None
    rule = _get_applicable_rule(store, category)

    rate = float(rule.rate) if rule else DEFAULT_COMMISSION_RATE
    flat_fee = float(rule.flat_fee) if rule else 0
    order_amount = float(order.total_amount)

    commission_amount = round(order_amount * rate + flat_fee, 2)
    vendor_amount = round(order_amount - commission_amount, 2)

    return {
        'rule': rule,
        'store': store,
        'order_amount': order_amount,
        'rate': rate,
        'flat_fee': flat_fee,
        'commission_amount': commission_amount,
        'vendor_amount': vendor_amount,
    }


@transaction.atomic
def create_commission_for_order(order):
    """Crée l'enregistrement Commission dès qu'une commande est complétée."""
    from .models import Commission

    if Commission.objects.filter(order=order).exists():
        return Commission.objects.get(order=order)

    data = calculate_commission(order)
    if not data['store']:
        return None

    commission = Commission.objects.create(
        order=order,
        store=data['store'],
        rule=data['rule'],
        order_amount=data['order_amount'],
        rate_applied=data['rate'],
        flat_fee_applied=data['flat_fee'],
        commission_amount=data['commission_amount'],
        vendor_amount=data['vendor_amount'],
        status='confirmed',
    )

    # Mettre à jour le wallet vendeur
    try:
        wallet = data['store'].user.wallet
        wallet.credit(
            amount=data['vendor_amount'],
            description=f'Vente — commande {order.order_number}',
            reference=order.order_number,
        )
    except Exception as e:
        logger.warning('Wallet credit failed for order %s: %s', order.order_number, e)

    return commission


@transaction.atomic
def create_vendor_payout(store, period_start, period_end, method='bank_transfer', processed_by=None):
    """Crée un reversement groupé pour un vendeur sur une période donnée."""
    from .models import Commission, VendorPayout

    commissions = Commission.objects.filter(
        store=store,
        status='confirmed',
        created_at__date__gte=period_start,
        created_at__date__lte=period_end,
    )

    if not commissions.exists():
        return None

    total_order = sum(c.order_amount for c in commissions)
    total_commission = sum(c.commission_amount for c in commissions)
    total_payout = sum(c.vendor_amount for c in commissions)

    payout = VendorPayout.objects.create(
        store=store,
        period_start=period_start,
        period_end=period_end,
        total_order_amount=total_order,
        total_commission=total_commission,
        total_payout=total_payout,
        method=method,
        processed_by=processed_by,
    )

    commissions.update(status='paid', paid_at=timezone.now(), payout=payout)

    # Notifier le vendeur
    try:
        from apps.notifications.models import Notification
        Notification.objects.create(
            user=store.user,
            title='Reversement reçu',
            message=f'Votre reversement de {total_payout} FCFA a été traité (réf: {payout.reference}).',
            notification_type='payment',
        )
    except Exception:
        pass

    return payout


def get_vendor_commission_summary(store, year=None, month=None):
    """Retourne un résumé des commissions pour une boutique."""
    from .models import Commission
    from django.db.models import Sum, Count, Q

    qs = Commission.objects.filter(store=store)
    if year:
        qs = qs.filter(created_at__year=year)
    if month:
        qs = qs.filter(created_at__month=month)

    return qs.aggregate(
        total_orders=Count('id'),
        total_order_amount=Sum('order_amount'),
        total_commission=Sum('commission_amount'),
        total_vendor_amount=Sum('vendor_amount'),
        paid_amount=Sum('vendor_amount', filter=Q(status='paid')),
        pending_amount=Sum('vendor_amount', filter=Q(status='confirmed')),
    )
