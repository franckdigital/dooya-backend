"""
Moteur de calcul BI — toutes les métriques d'audit calculées depuis les données réelles.
Chaque fonction retourne un dict serialisable, jamais de modèles ORM.
"""
from datetime import datetime as _dt
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import (
    Sum, Avg, Count, F, Q, Min, Max, FloatField, DecimalField as DField
)
from django.db.models.functions import TruncDate, Coalesce
from django.utils import timezone
import calendar


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _period_bounds(year: int, month: int):
    """Retourne (start_dt, end_dt_exclusive) pour un mois — datetimes timezone-aware.
    Utilise __gte / __lt pour éviter CONVERT_TZ() de MySQL (incompatible sans tzdata)."""
    start = timezone.make_aware(_dt(year, month, 1))
    if month == 12:
        end = timezone.make_aware(_dt(year + 1, 1, 1))
    else:
        end = timezone.make_aware(_dt(year, month + 1, 1))
    return start, end


def _prev_month(year: int, month: int):
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _pct_variation(current, previous):
    """Variation % arrondie à 1 décimale. Retourne None si précédent = 0."""
    try:
        c, p = float(current or 0), float(previous or 0)
        if p == 0:
            return 100.0 if c > 0 else 0.0
        return round((c - p) / p * 100, 1)
    except Exception:
        return 0.0


def _trend(variation_pct):
    """'up' / 'down' / 'stable' selon la variation."""
    if variation_pct is None:
        return 'stable'
    v = float(variation_pct)
    if v > 2:
        return 'up'
    if v < -2:
        return 'down'
    return 'stable'


def _d(val, places=2):
    """Arrondit un Decimal ou float."""
    try:
        return float(Decimal(str(val or 0)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        ))
    except Exception:
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
#  Calcul des métriques ventes
# ─────────────────────────────────────────────────────────────────────────────

def compute_sales_metrics(year: int, month: int, store=None) -> dict:
    from apps.orders.models import Order, OrderItem

    start, end = _period_bounds(year, month)
    qs = Order.objects.filter(created_at__gte=start, created_at__lt=end)
    if store:
        qs = qs.filter(items__store=store).distinct()

    agg = qs.aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='delivered')),
        cancelled=Count('id', filter=Q(status='cancelled')),
        refunded=Count('id', filter=Q(status='refunded')),
        pending=Count('id', filter=Q(status__in=('pending', 'confirmed', 'processing', 'shipped'))),
        revenue=Coalesce(Sum('total_amount', filter=Q(status='delivered')), Decimal('0')),
    )

    revenue = _d(agg['revenue'])
    completed = agg['completed'] or 0
    total = agg['total'] or 0
    aov = _d(revenue / completed) if completed else 0.0
    conv = _d(completed / total * 100) if total else 0.0

    # Commissions
    if store:
        rate = float(store.commission_rate)
    else:
        from django.conf import settings
        rate = float(getattr(settings, 'MARKETPLACE_COMMISSION_RATE', 0.10))
    commissions = _d(revenue * rate)

    # Revenu journalier (courbe sur le mois)
    try:
        daily = list(
            qs.filter(status='delivered')
              .annotate(day=TruncDate('created_at'))
              .values('day')
              .annotate(rev=Coalesce(Sum('total_amount'), Decimal('0')), cnt=Count('id'))
              .order_by('day')
        )
        daily = [d for d in daily if d['day'] is not None]
    except Exception:
        daily = []

    return {
        'revenue': revenue,
        'orders_total': total,
        'orders_completed': completed,
        'orders_cancelled': agg['cancelled'] or 0,
        'orders_refunded': agg['refunded'] or 0,
        'orders_pending': agg['pending'] or 0,
        'average_order_value': aov,
        'conversion_rate': conv,
        'commissions': commissions,
        'daily_revenue': [
            {'date': str(d['day']), 'revenue': _d(d['rev']), 'orders': d['cnt']}
            for d in daily
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Métriques clients
# ─────────────────────────────────────────────────────────────────────────────

def compute_customer_metrics(year: int, month: int, store=None) -> dict:
    from apps.orders.models import Order
    from apps.cart.models import Cart
    from django.contrib.auth import get_user_model
    User = get_user_model()

    start, end = _period_bounds(year, month)

    # Clients ayant commandé ce mois
    orders_qs = Order.objects.filter(
        created_at__gte=start,
        created_at__lt=end,
    )
    if store:
        orders_qs = orders_qs.filter(items__store=store).distinct()

    active_ids = set(orders_qs.values_list('user_id', flat=True))
    total_active = len(active_ids)

    # Nouveaux vs récurrents
    new_ids = set(
        User.objects.filter(
            date_joined__gte=start,
            date_joined__lt=end,
            id__in=active_ids,
        ).values_list('id', flat=True)
    )
    new_customers = len(new_ids)
    returning_customers = total_active - new_customers

    # Fréquence d'achat moyenne
    freq_agg = orders_qs.values('user_id').annotate(cnt=Count('id'))
    avg_freq = _d(
        sum(r['cnt'] for r in freq_agg) / len(freq_agg)
    ) if freq_agg else 0.0

    # Abandon panier — carts créés ce mois sans commande
    try:
        carts_with_items = Cart.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
            items__isnull=False,
        ).distinct().count()
        carts_with_orders = orders_qs.filter(
            user__isnull=False
        ).values('user_id').distinct().count()
        cart_abandonment = _d(
            (1 - carts_with_orders / carts_with_items) * 100
        ) if carts_with_items else 0.0
    except Exception:
        cart_abandonment = 0.0

    # Clients qui ont commandé M-1 mais pas ce mois (churn approximatif)
    prev_y, prev_m = _prev_month(year, month)
    prev_start, prev_end = _period_bounds(prev_y, prev_m)
    prev_active = set(
        Order.objects.filter(
            created_at__gte=prev_start,
            created_at__lt=prev_end,
        ).values_list('user_id', flat=True)
    )
    churned = len(prev_active - active_ids)
    retention_rate = _d(
        len(prev_active & active_ids) / len(prev_active) * 100
    ) if prev_active else 0.0

    # Top clients par CA
    top_customers = list(
        orders_qs.filter(status='delivered')
                 .values('user_id', 'user__first_name', 'user__last_name', 'user__email')
                 .annotate(total_spent=Sum('total_amount'), orders=Count('id'))
                 .order_by('-total_spent')[:10]
    )

    return {
        'new_customers': new_customers,
        'returning_customers': returning_customers,
        'total_active_customers': total_active,
        'churned_customers': churned,
        'retention_rate': retention_rate,
        'cart_abandonment_rate': cart_abandonment,
        'avg_purchase_frequency': avg_freq,
        'top_customers': [
            {
                'user_id': r['user_id'],
                'name': f"{r['user__first_name']} {r['user__last_name']}".strip(),
                'email': r['user__email'],
                'total_spent': _d(r['total_spent']),
                'orders': r['orders'],
            }
            for r in top_customers
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Métriques produits
# ─────────────────────────────────────────────────────────────────────────────

def compute_product_metrics(year: int, month: int, store=None) -> dict:
    from apps.orders.models import OrderItem
    from apps.products.models import Product

    start, end = _period_bounds(year, month)

    items_qs = OrderItem.objects.filter(
        order__created_at__gte=start,
        order__created_at__lt=end,
        order__status='delivered',
    )
    if store:
        items_qs = items_qs.filter(store=store)

    agg = items_qs.aggregate(
        units=Coalesce(Sum('quantity'), 0),
        unique=Count('product_id', distinct=True),
        revenue=Coalesce(Sum('total_price'), Decimal('0')),
    )

    # Top 10 produits par CA
    top_by_revenue = list(
        items_qs.values('product_id', 'product_name')
                .annotate(rev=Sum('total_price'), qty=Sum('quantity'))
                .order_by('-rev')[:10]
    )

    # Top 10 par unités vendues
    top_by_units = list(
        items_qs.values('product_id', 'product_name')
                .annotate(qty=Sum('quantity'))
                .order_by('-qty')[:10]
    )

    # Produits en rupture de stock
    products_qs = Product.objects.filter(is_active=True)
    if store:
        products_qs = products_qs.filter(store=store)
    stockout_count = products_qs.filter(stock=0).count()
    low_stock_count = products_qs.filter(stock__gt=0, stock__lte=F('min_stock_alert')).count()

    # Produits sans vente ce mois (articles lents)
    sold_ids = set(items_qs.values_list('product_id', flat=True))
    slow_movers_count = products_qs.exclude(id__in=sold_ids).count()

    # Catégories les plus performantes
    top_categories = list(
        items_qs.filter(product__category__isnull=False)
                .values('product__category__name', 'product__category__slug')
                .annotate(rev=Sum('total_price'), qty=Sum('quantity'))
                .order_by('-rev')[:10]
    )

    return {
        'units_sold': agg['units'],
        'unique_products_sold': agg['unique'],
        'total_product_revenue': _d(agg['revenue']),
        'stockout_products': stockout_count,
        'low_stock_products': low_stock_count,
        'slow_movers': slow_movers_count,
        'top_products_by_revenue': [
            {'product_id': r['product_id'], 'name': r['product_name'],
             'revenue': _d(r['rev']), 'units': r['qty']}
            for r in top_by_revenue
        ],
        'top_products_by_units': [
            {'product_id': r['product_id'], 'name': r['product_name'], 'units': r['qty']}
            for r in top_by_units
        ],
        'top_categories': [
            {'category': r['product__category__name'],
             'slug': r['product__category__slug'],
             'revenue': _d(r['rev']), 'units': r['qty']}
            for r in top_categories
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Métriques vendeurs
# ─────────────────────────────────────────────────────────────────────────────

def compute_vendor_metrics(year: int, month: int, store=None) -> dict:
    from apps.orders.models import OrderItem, Order
    from apps.vendors.models import Store
    from apps.reviews.models import StoreReview

    start, end = _period_bounds(year, month)

    items_qs = OrderItem.objects.filter(
        order__created_at__gte=start,
        order__created_at__lt=end,
        order__status='delivered',
    )
    if store:
        items_qs = items_qs.filter(store=store)

    # Performance par boutique
    store_stats = list(
        items_qs.values('store_id', 'store__name')
                .annotate(
                    revenue=Sum('total_price'),
                    orders=Count('order_id', distinct=True),
                    units=Sum('quantity'),
                )
                .order_by('-revenue')[:20]
    )

    # Taux de fulfillment par boutique (livré / total)
    all_orders = Order.objects.filter(
        created_at__gte=start,
        created_at__lt=end,
    )
    if store:
        all_orders = all_orders.filter(items__store=store).distinct()

    fulfillment = list(
        all_orders.values('items__store_id', 'items__store__name')
                  .annotate(
                      total=Count('id', distinct=True),
                      delivered=Count('id', filter=Q(status='delivered'), distinct=True),
                  )
                  .order_by('-total')[:20]
    )

    # Retours par boutique
    try:
        from apps.quality.models import ProductReturn
        returns_qs = ProductReturn.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
            status__in=('approved', 'completed', 'refunded', 'restocked'),
        )
        returns_by_store = dict(
            returns_qs.values('product__store_id')
                      .annotate(cnt=Count('id'))
                      .values_list('product__store_id', 'cnt')
        )
    except Exception:
        returns_by_store = {}

    vendors = []
    for s in store_stats:
        store_id = s['store_id']
        store_name = s['store__name']
        total_delivered = next(
            (f['delivered'] for f in fulfillment if f['items__store_id'] == store_id), 0
        )
        total_all = next(
            (f['total'] for f in fulfillment if f['items__store_id'] == store_id), 1
        )
        fulfillment_rate = _d(total_delivered / total_all * 100) if total_all else 0
        returns = returns_by_store.get(store_id, 0)
        return_rate = _d(returns / s['orders'] * 100) if s['orders'] else 0

        vendors.append({
            'store_id': store_id,
            'store_name': store_name,
            'revenue': _d(s['revenue']),
            'orders': s['orders'],
            'units_sold': s['units'],
            'fulfillment_rate': fulfillment_rate,
            'return_rate': return_rate,
            'returns_count': returns,
        })

    global_revenue = sum(v['revenue'] for v in vendors)
    return {
        'vendors': vendors,
        'total_active_vendors': len(vendors),
        'global_vendor_revenue': _d(global_revenue),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Métriques qualité & retours
# ─────────────────────────────────────────────────────────────────────────────

def compute_quality_metrics(year: int, month: int, store=None) -> dict:
    start, end = _period_bounds(year, month)

    try:
        from apps.quality.models import ProductReturn, QualityInspection
        returns_qs = ProductReturn.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
        )
        if store:
            returns_qs = returns_qs.filter(product__store=store)

        returns_agg = returns_qs.aggregate(
            total=Count('id'),
            approved=Count('id', filter=Q(status__in=('approved', 'completed', 'refunded', 'restocked'))),
            rejected=Count('id', filter=Q(status='rejected')),
            pending=Count('id', filter=Q(status='pending')),
        )

        # Motifs de retour
        reasons = list(
            returns_qs.values('reason')
                      .annotate(cnt=Count('id'))
                      .order_by('-cnt')
        )

        # Conditions produits retournés
        conditions = list(
            returns_qs.values('condition')
                      .annotate(cnt=Count('id'))
                      .order_by('-cnt')
        )

        inspections_qs = QualityInspection.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
        )
        if store:
            inspections_qs = inspections_qs.filter(product__store=store)

        insp_agg = inspections_qs.aggregate(
            total=Count('id'),
            passed=Count('id', filter=Q(result='passed')),
            failed=Count('id', filter=Q(result='failed')),
            partial=Count('id', filter=Q(result='partial')),
        )
        pass_rate = _d(
            insp_agg['passed'] / insp_agg['total'] * 100
        ) if insp_agg['total'] else 0.0

    except Exception:
        returns_agg = {'total': 0, 'approved': 0, 'rejected': 0, 'pending': 0}
        insp_agg = {'total': 0, 'passed': 0, 'failed': 0, 'partial': 0}
        pass_rate = 0.0
        reasons = []
        conditions = []

    try:
        from apps.support.models import Dispute
        disputes_qs = Dispute.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
        )
        if store:
            disputes_qs = disputes_qs.filter(defendant_store=store)

        disputes_agg = disputes_qs.aggregate(
            opened=Count('id'),
            resolved=Count('id', filter=Q(status__in=(
                'resolved_buyer', 'resolved_seller', 'resolved_partial', 'closed'
            ))),
        )
        avg_resolution = 0.0
        resolved_qs = disputes_qs.filter(
            resolved_at__isnull=False
        ).annotate(days=F('resolved_at') - F('created_at'))
        # Calcul approximatif du délai
        if resolved_qs.exists():
            from django.db.models.functions import Extract
            avg_sec = resolved_qs.aggregate(
                avg=Avg(
                    Extract(F('resolved_at') - F('created_at'), 'epoch')
                )
            )['avg'] or 0
            avg_resolution = _d(avg_sec / 86400)
    except Exception:
        disputes_agg = {'opened': 0, 'resolved': 0}
        avg_resolution = 0.0

    from apps.orders.models import Order
    orders_count = Order.objects.filter(
        created_at__gte=start,
        created_at__lt=end,
        status='delivered',
    ).count()
    if store:
        orders_count = Order.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
            status='delivered',
            items__store=store,
        ).distinct().count()

    return_rate = _d(
        returns_agg['total'] / orders_count * 100
    ) if orders_count else 0.0

    return {
        'returns_total': returns_agg['total'],
        'returns_approved': returns_agg['approved'],
        'returns_rejected': returns_agg['rejected'],
        'returns_pending': returns_agg['pending'],
        'return_rate': return_rate,
        'top_return_reasons': [
            {'reason': r['reason'], 'count': r['cnt']} for r in reasons
        ],
        'return_conditions': [
            {'condition': r['condition'], 'count': r['cnt']} for r in conditions
        ],
        'inspections_total': insp_agg['total'],
        'inspections_passed': insp_agg['passed'],
        'inspections_failed': insp_agg['failed'],
        'inspection_pass_rate': pass_rate,
        'disputes_opened': disputes_agg['opened'],
        'disputes_resolved': disputes_agg['resolved'],
        'avg_dispute_resolution_days': avg_resolution,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Métriques livraison
# ─────────────────────────────────────────────────────────────────────────────

def compute_delivery_metrics(year: int, month: int, store=None) -> dict:
    from apps.orders.models import Order

    start, end = _period_bounds(year, month)

    delivered_qs = Order.objects.filter(
        created_at__gte=start,
        created_at__lt=end,
        status='delivered',
    )
    if store:
        delivered_qs = delivered_qs.filter(items__store=store).distinct()

    total_delivered = delivered_qs.count()

    # Délai de livraison approximatif via l'historique des statuts
    try:
        from apps.orders.models import OrderStatusHistory
        # Trouver la date de passage à 'shipped' et 'delivered'
        shipped_dates = dict(
            OrderStatusHistory.objects.filter(
                order__in=delivered_qs, status='shipped'
            ).values('order_id').annotate(d=Min('created_at')).values_list('order_id', 'd')
        )
        delivered_dates = dict(
            OrderStatusHistory.objects.filter(
                order__in=delivered_qs, status='delivered'
            ).values('order_id').annotate(d=Min('created_at')).values_list('order_id', 'd')
        )
        delays = []
        for oid, ship_dt in shipped_dates.items():
            if oid in delivered_dates:
                delta = (delivered_dates[oid] - ship_dt).total_seconds() / 86400
                if 0 <= delta <= 60:
                    delays.append(delta)
        avg_delivery_days = _d(sum(delays) / len(delays)) if delays else 0.0
    except Exception:
        avg_delivery_days = 0.0

    # Taux de livraison à temps (< 7 jours approximatif)
    on_time = sum(1 for d in delays if d <= 7) if 'delays' in dir() and delays else 0
    on_time_rate = _d(on_time / len(delays) * 100) if 'delays' in dir() and delays else 0.0

    try:
        from apps.deliveries.models import Delivery
        deliveries_qs = Delivery.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
        )
        if store:
            deliveries_qs = deliveries_qs.filter(order__items__store=store).distinct()

        delivery_agg = deliveries_qs.aggregate(
            total=Count('id'),
            delivered=Count('id', filter=Q(status='delivered')),
            failed=Count('id', filter=Q(status__in=('failed', 'returned'))),
        )
        delivery_success_rate = _d(
            delivery_agg['delivered'] / delivery_agg['total'] * 100
        ) if delivery_agg['total'] else 0.0
    except Exception:
        delivery_agg = {'total': 0, 'delivered': 0, 'failed': 0}
        delivery_success_rate = 0.0

    return {
        'total_delivered_orders': total_delivered,
        'avg_delivery_days': avg_delivery_days,
        'on_time_delivery_rate': on_time_rate,
        'delivery_success_rate': delivery_success_rate,
        'delivery_failures': delivery_agg.get('failed', 0),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Métriques support
# ─────────────────────────────────────────────────────────────────────────────

def compute_support_metrics(year: int, month: int) -> dict:
    start, end = _period_bounds(year, month)
    try:
        from apps.support.models import SupportTicket
        qs = SupportTicket.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
        )
        agg = qs.aggregate(
            total=Count('id'),
            resolved=Count('id', filter=Q(status__in=('resolved', 'closed'))),
            open_count=Count('id', filter=Q(status='open')),
        )
        avg_satisfaction = qs.filter(
            satisfaction_score__isnull=False
        ).aggregate(avg=Avg('satisfaction_score'))['avg'] or 0
        resolution_rate = _d(
            agg['resolved'] / agg['total'] * 100
        ) if agg['total'] else 0.0

        by_category = list(
            qs.values('category').annotate(cnt=Count('id')).order_by('-cnt')
        )
    except Exception:
        agg = {'total': 0, 'resolved': 0, 'open_count': 0}
        avg_satisfaction = 0
        resolution_rate = 0.0
        by_category = []

    return {
        'tickets_total': agg['total'],
        'tickets_resolved': agg['resolved'],
        'tickets_open': agg['open_count'],
        'resolution_rate': resolution_rate,
        'avg_satisfaction_score': _d(avg_satisfaction),
        'tickets_by_category': [
            {'category': r['category'], 'count': r['cnt']} for r in by_category
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Fonction centrale : calcul complet + comparaison M vs M-1
# ─────────────────────────────────────────────────────────────────────────────

def compute_full_metrics(year: int, month: int, store=None) -> dict:
    """Calcule tous les KPIs pour le mois donné."""
    return {
        'period': {'year': year, 'month': month},
        'sales': compute_sales_metrics(year, month, store),
        'customers': compute_customer_metrics(year, month, store),
        'products': compute_product_metrics(year, month, store),
        'vendors': compute_vendor_metrics(year, month, store),
        'quality': compute_quality_metrics(year, month, store),
        'delivery': compute_delivery_metrics(year, month, store),
        'support': compute_support_metrics(year, month),
    }


def compare_months(year: int, month: int, store=None) -> dict:
    """
    Retourne les métriques du mois courant ET du mois précédent avec
    les variations absolues et % pour chaque indicateur clé.
    """
    prev_y, prev_m = _prev_month(year, month)

    current = compute_full_metrics(year, month, store)
    previous = _get_previous_metrics(prev_y, prev_m, store)

    def delta(section, key):
        cur = current[section].get(key, 0) or 0
        prv = (previous.get(section) or {}).get(key, 0) or 0
        var = _pct_variation(cur, prv)
        return {
            'current': cur,
            'previous': prv,
            'variation_pct': var,
            'trend': _trend(var),
        }

    comparison = {
        'period': {
            'current': {'year': year, 'month': month},
            'previous': {'year': prev_y, 'month': prev_m},
        },
        'sales': {
            'revenue': delta('sales', 'revenue'),
            'orders_total': delta('sales', 'orders_total'),
            'orders_completed': delta('sales', 'orders_completed'),
            'orders_cancelled': delta('sales', 'orders_cancelled'),
            'average_order_value': delta('sales', 'average_order_value'),
            'conversion_rate': delta('sales', 'conversion_rate'),
            'commissions': delta('sales', 'commissions'),
        },
        'customers': {
            'new_customers': delta('customers', 'new_customers'),
            'returning_customers': delta('customers', 'returning_customers'),
            'total_active': delta('customers', 'total_active_customers'),
            'churn': delta('customers', 'churned_customers'),
            'cart_abandonment_rate': delta('customers', 'cart_abandonment_rate'),
            'retention_rate': delta('customers', 'retention_rate'),
        },
        'products': {
            'units_sold': delta('products', 'units_sold'),
            'unique_products_sold': delta('products', 'unique_products_sold'),
            'stockout_products': delta('products', 'stockout_products'),
            'slow_movers': delta('products', 'slow_movers'),
        },
        'quality': {
            'returns_total': delta('quality', 'returns_total'),
            'return_rate': delta('quality', 'return_rate'),
            'disputes_opened': delta('quality', 'disputes_opened'),
            'inspection_pass_rate': delta('quality', 'inspection_pass_rate'),
        },
        'delivery': {
            'avg_delivery_days': delta('delivery', 'avg_delivery_days'),
            'on_time_delivery_rate': delta('delivery', 'on_time_delivery_rate'),
        },
        'support': {
            'tickets_total': delta('support', 'tickets_total'),
            'resolution_rate': delta('support', 'resolution_rate'),
            'avg_satisfaction': delta('support', 'avg_satisfaction_score'),
        },
        # Détails complets des deux mois
        'current_detail': current,
        'previous_detail': previous,
    }

    comparison['insights'] = generate_insights(comparison)
    return comparison


def _get_previous_metrics(year: int, month: int, store=None) -> dict:
    """Essaie d'abord le snapshot stocké, sinon recalcule."""
    from apps.audit.models import MonthlySnapshot
    try:
        snap = MonthlySnapshot.objects.get(year=year, month=month, store=store)
        return _snapshot_to_dict(snap)
    except MonthlySnapshot.DoesNotExist:
        return compute_full_metrics(year, month, store)


def _snapshot_to_dict(snap) -> dict:
    return {
        'sales': {
            'revenue': float(snap.revenue),
            'orders_total': snap.orders_total,
            'orders_completed': snap.orders_completed,
            'orders_cancelled': snap.orders_cancelled,
            'orders_refunded': snap.orders_refunded,
            'average_order_value': float(snap.average_order_value),
            'conversion_rate': float(snap.conversion_rate),
            'commissions': float(snap.commissions),
        },
        'customers': {
            'new_customers': snap.new_customers,
            'returning_customers': snap.returning_customers,
            'total_active_customers': snap.total_active_customers,
            'churned_customers': 0,
            'retention_rate': 0,
            'cart_abandonment_rate': float(snap.cart_abandonment_rate),
        },
        'products': {
            'units_sold': snap.units_sold,
            'unique_products_sold': snap.unique_products_sold,
            'stockout_products': snap.stockout_products,
            'slow_movers': 0,
        },
        'quality': {
            'returns_total': snap.returns_count,
            'return_rate': float(snap.return_rate),
            'disputes_opened': snap.disputes_opened,
            'inspection_pass_rate': 0,
        },
        'delivery': {
            'avg_delivery_days': float(snap.avg_delivery_days),
            'on_time_delivery_rate': float(snap.on_time_delivery_rate),
        },
        'support': {
            'tickets_total': snap.support_tickets,
            'resolution_rate': 0,
            'avg_satisfaction_score': 0,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Génération d'insights automatiques
# ─────────────────────────────────────────────────────────────────────────────

def generate_insights(comparison: dict) -> list:
    """
    Génère une liste d'insights textuels avec niveau de priorité
    basés sur les variations et les seuils critiques.
    """
    insights = []

    def _v(section, key):
        return comparison.get(section, {}).get(key, {})

    def add(level, category, title, detail, recommendation=''):
        insights.append({
            'level': level,
            'category': category,
            'title': title,
            'detail': detail,
            'recommendation': recommendation,
        })

    # ── Ventes ────────────────────────────────────────────────────────────────
    rev = _v('sales', 'revenue')
    if rev.get('variation_pct', 0) < -10:
        add('critical', 'sales',
            f"Chute du CA de {abs(rev['variation_pct'])}%",
            f"Revenus: {rev['current']:,.0f} XOF vs {rev['previous']:,.0f} XOF le mois dernier.",
            "Analysez les catégories en baisse et relancez les campagnes promotionnelles.")

    aov = _v('sales', 'average_order_value')
    if aov.get('variation_pct', 0) < -15:
        add('warning', 'sales',
            f"Panier moyen en baisse de {abs(aov['variation_pct'])}%",
            f"Panier moyen: {aov['current']:,.0f} vs {aov['previous']:,.0f} XOF.",
            "Proposez des offres de bundle ou de la vente croisée.")

    conv = _v('sales', 'conversion_rate')
    if float(conv.get('current', 0)) < 30:
        add('warning', 'sales',
            f"Taux de conversion faible: {conv['current']}%",
            "Moins de 30% des commandes sont finalisées.",
            "Vérifiez les frictions dans le tunnel de commande (paiement, livraison).")

    # ── Clients ───────────────────────────────────────────────────────────────
    churn = _v('customers', 'churn')
    if churn.get('variation_pct', 0) > 20:
        add('critical', 'customers',
            f"Pic de churn: +{churn['variation_pct']}% de clients perdus",
            f"{churn['current']} clients n'ont pas commandé ce mois vs {churn['previous']} le mois dernier.",
            "Lancez une campagne de réactivation avec une offre personnalisée.")

    cart = _v('customers', 'cart_abandonment_rate')
    if float(cart.get('current', 0)) > 65:
        add('warning', 'customers',
            f"Abandon panier élevé: {cart['current']}%",
            "Plus de 2/3 des paniers ne sont pas convertis.",
            "Envoyez des emails de relance panier et simplifiez le checkout.")

    # ── Qualité ───────────────────────────────────────────────────────────────
    ret_rate = _v('quality', 'return_rate')
    if float(ret_rate.get('current', 0)) > 8:
        add('critical', 'quality',
            f"Taux de retour critique: {ret_rate['current']}%",
            f"{ret_rate['current']}% des commandes livrées ont été retournées.",
            "Auditez les produits avec le plus de retours. Améliorez les descriptions et les contrôles qualité.")
    elif ret_rate.get('variation_pct', 0) > 30:
        add('warning', 'quality',
            f"Taux de retour en hausse de {ret_rate['variation_pct']}%",
            f"Passé de {ret_rate['previous']}% à {ret_rate['current']}%.",
            "Identifiez les produits ou vendeurs à l'origine de l'augmentation des retours.")

    disputes = _v('quality', 'disputes_opened')
    if disputes.get('variation_pct', 0) > 50:
        add('critical', 'quality',
            f"Pic de contentieux: +{disputes['variation_pct']}%",
            f"{disputes['current']} contentieux ouverts vs {disputes['previous']} le mois dernier.",
            "Traitez en urgence les litiges en cours et identifiez les vendeurs impliqués.")

    # ── Livraison ─────────────────────────────────────────────────────────────
    otd = _v('delivery', 'on_time_delivery_rate')
    if float(otd.get('current', 0)) < 80:
        add('warning', 'delivery',
            f"Livraisons à temps insuffisantes: {otd['current']}%",
            "Moins de 80% des livraisons respectent les délais annoncés.",
            "Révisez les partenariats logistiques et les délais affichés sur le site.")

    avg_del = _v('delivery', 'avg_delivery_days')
    if avg_del.get('variation_pct', 0) > 25:
        add('warning', 'delivery',
            f"Délai moyen de livraison en hausse: +{avg_del['variation_pct']}%",
            f"{avg_del['current']:.1f} jours vs {avg_del['previous']:.1f} jours le mois dernier.",
            "Vérifiez les transporteurs et les zones géographiques problématiques.")

    # ── Support ───────────────────────────────────────────────────────────────
    sat = _v('support', 'avg_satisfaction')
    if float(sat.get('current', 5)) < 3.5:
        add('warning', 'support',
            f"Satisfaction support faible: {sat['current']:.1f}/5",
            "La note de satisfaction du support est en dessous de 3.5/5.",
            "Formez les agents, réduisez les délais de réponse et personnalisez les réponses.")

    # ── Produits ──────────────────────────────────────────────────────────────
    stockout = _v('products', 'stockout_products')
    if int(stockout.get('current', 0)) > 10:
        add('warning', 'products',
            f"{stockout['current']} produits en rupture de stock",
            "Des ruptures fréquentes dégradent l'expérience client et le CA.",
            "Activez le réapprovisionnement automatique et alertez les vendeurs concernés.")

    # Trier par priorité : critical > warning > info
    order = {'critical': 0, 'warning': 1, 'info': 2}
    insights.sort(key=lambda x: order.get(x['level'], 3))
    return insights


# ─────────────────────────────────────────────────────────────────────────────
#  Sauvegarde du snapshot mensuel
# ─────────────────────────────────────────────────────────────────────────────

def save_monthly_snapshot(year: int, month: int, store=None):
    """
    Calcule et sauvegarde (upsert) le snapshot mensuel.
    Appelé par la tâche Celery le 1er de chaque mois.
    """
    from apps.audit.models import MonthlySnapshot
    metrics = compute_full_metrics(year, month, store)
    s = metrics['sales']
    c = metrics['customers']
    p = metrics['products']
    q = metrics['quality']
    d = metrics['delivery']
    sup = metrics['support']

    snap, _ = MonthlySnapshot.objects.update_or_create(
        year=year, month=month, store=store,
        defaults={
            'revenue': s['revenue'],
            'orders_total': s['orders_total'],
            'orders_completed': s['orders_completed'],
            'orders_cancelled': s['orders_cancelled'],
            'orders_refunded': s['orders_refunded'],
            'orders_pending': s['orders_pending'],
            'average_order_value': s['average_order_value'],
            'commissions': s['commissions'],
            'conversion_rate': s['conversion_rate'],
            'new_customers': c['new_customers'],
            'returning_customers': c['returning_customers'],
            'total_active_customers': c['total_active_customers'],
            'cart_abandonment_rate': c['cart_abandonment_rate'],
            'avg_purchase_frequency': c['avg_purchase_frequency'],
            'units_sold': p['units_sold'],
            'unique_products_sold': p['unique_products_sold'],
            'stockout_products': p['stockout_products'],
            'returns_count': q['returns_total'],
            'return_rate': q['return_rate'],
            'disputes_opened': q['disputes_opened'],
            'disputes_resolved': q['disputes_resolved'],
            'failed_inspections': q['inspections_failed'] if 'inspections_failed' in q else 0,
            'avg_delivery_days': d['avg_delivery_days'],
            'on_time_delivery_rate': d['on_time_delivery_rate'],
            'support_tickets': sup['tickets_total'],
        },
    )
    _generate_kpi_alerts(year, month, store)
    return snap


# ─────────────────────────────────────────────────────────────────────────────
#  Génération automatique d'alertes KPI
# ─────────────────────────────────────────────────────────────────────────────

def _generate_kpi_alerts(year: int, month: int, store=None):
    """Crée les alertes KPI pour les métriques critiques détectées."""
    from apps.audit.models import KPIAlert
    comparison = compare_months(year, month, store)
    insights = comparison.get('insights', [])

    # Supprimer les anciennes alertes non acquittées du même mois
    KPIAlert.objects.filter(
        year=year, month=month, store=store, is_acknowledged=False
    ).delete()

    for insight in insights:
        if insight['level'] in ('warning', 'critical'):
            severity = insight['level']
            KPIAlert.objects.create(
                title=insight['title'],
                description=insight['detail'],
                recommendations=insight['recommendation'],
                category=insight['category'],
                severity=severity,
                metric_name=insight['category'],
                current_value=0,
                previous_value=0,
                variation_pct=0,
                threshold=0,
                store=store,
                year=year,
                month=month,
            )
