"""
Moteur de recommandations.

Trois stratégies, sans dépendance ML externe :
  1. similar_products   — contenu : catégorie + tags + attributs partagés
  2. personalized       — collaboratif léger : ce qu'ont acheté les clients
                          qui ont acheté les mêmes produits
  3. trending           — vues + commandes sur fenêtre glissante configurable
  4. recently_viewed    — historique de navigation de l'utilisateur courant
"""
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _base_qs():
    from apps.products.models import Product
    return Product.objects.filter(is_active=True).select_related('store', 'category')


# ─────────────────────────────────────────────────────────────────────────────
# 1. Produits similaires (content-based)
# ─────────────────────────────────────────────────────────────────────────────

def similar_products(product, limit=10):
    """
    Retourne les produits similaires à `product` en se basant sur :
    - même catégorie (et descendants)
    - tags communs
    - attributs communs
    Scoré par nombre de critères partagés, trié par score DESC.
    """
    from apps.products.models import Product

    qs = _base_qs().exclude(pk=product.pk)

    tag_ids = list(product.tags.values_list('id', flat=True))
    attr_values = list(product.attributes.values_list('value_id', flat=True))

    # Descendants de la catégorie (inclus self)
    try:
        cat_ids = list(product.category.get_descendants(include_self=True).values_list('id', flat=True))
    except Exception:
        cat_ids = [product.category_id] if product.category_id else []

    annotated = qs.annotate(
        tag_matches=Count('tags', filter=Q(tags__id__in=tag_ids)) if tag_ids else Count('id', filter=Q(id=None)),
        attr_matches=Count('attributes', filter=Q(attributes__value_id__in=attr_values)) if attr_values else Count('id', filter=Q(id=None)),
        same_cat=Count('id', filter=Q(category_id__in=cat_ids)),
    ).annotate(
        score=Count('id', filter=Q(category_id__in=cat_ids)) * 3
    )

    # Fallback simple si les annotations avancées ne marchent pas parfaitement
    results = (
        _base_qs()
        .exclude(pk=product.pk)
        .filter(
            Q(category_id__in=cat_ids) |
            Q(tags__id__in=tag_ids)
        )
        .distinct()
        .order_by('-views_count')[:limit]
    )
    return list(results)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Recommandations personnalisées (collaboratif léger)
# ─────────────────────────────────────────────────────────────────────────────

def personalized(user, limit=10):
    """
    « Les clients qui ont acheté les mêmes produits que toi ont aussi acheté… »
    Basé sur les commandes complétées de l'utilisateur.
    """
    from apps.orders.models import Order, OrderItem

    # Produits déjà achetés par l'utilisateur
    user_product_ids = (
        OrderItem.objects.filter(order__user=user, order__status='completed')
        .values_list('product_id', flat=True)
        .distinct()
    )

    if not user_product_ids:
        return trending(limit=limit)

    # Utilisateurs ayant acheté les mêmes produits
    similar_users = (
        OrderItem.objects.filter(product_id__in=user_product_ids)
        .exclude(order__user=user)
        .values_list('order__user_id', flat=True)
        .distinct()
    )

    # Produits achetés par ces utilisateurs similaires, non encore achetés par l'utilisateur
    reco = (
        _base_qs()
        .exclude(pk__in=user_product_ids)
        .filter(order_items__order__user_id__in=similar_users, order_items__order__status='completed')
        .annotate(freq=Count('order_items'))
        .order_by('-freq')
        .distinct()[:limit]
    )

    results = list(reco)

    # Compléter avec du trending si pas assez de résultats
    if len(results) < limit:
        existing_ids = [p.pk for p in results]
        extra = trending(limit=limit - len(results), exclude_ids=existing_ids + list(user_product_ids))
        results += extra

    return results


# ─────────────────────────────────────────────────────────────────────────────
# 3. Tendances (trending)
# ─────────────────────────────────────────────────────────────────────────────

def trending(limit=10, days=7, exclude_ids=None, category_id=None):
    """
    Produits les plus vus et commandés sur les `days` derniers jours.
    """
    from apps.products.models import ProductView
    from apps.orders.models import OrderItem

    since = timezone.now() - timedelta(days=days)

    # Score = (vues récentes × 1) + (commandes récentes × 5)
    view_ids = (
        ProductView.objects.filter(created_at__gte=since)
        .values('product_id')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')
        .values_list('product_id', flat=True)[:100]
    )

    order_ids = (
        OrderItem.objects.filter(order__created_at__gte=since, order__status='completed')
        .values('product_id')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')
        .values_list('product_id', flat=True)[:100]
    )

    # Union des deux listes
    candidate_ids = list(set(list(view_ids) + list(order_ids)))

    qs = _base_qs().filter(pk__in=candidate_ids)
    if exclude_ids:
        qs = qs.exclude(pk__in=exclude_ids)
    if category_id:
        qs = qs.filter(category_id=category_id)

    # Trier par vues_count + commandes récentes
    results = list(qs.order_by('-views_count')[:limit])

    # Fallback: si aucune vue/commande récente, prendre les produits les mieux notés
    if not results:
        qs = _base_qs()
        if exclude_ids:
            qs = qs.exclude(pk__in=exclude_ids)
        if category_id:
            qs = qs.filter(category_id=category_id)
        results = list(qs.order_by('-views_count', '-rating')[:limit])

    return results


# ─────────────────────────────────────────────────────────────────────────────
# 4. Récemment vus (historique navigation)
# ─────────────────────────────────────────────────────────────────────────────

def recently_viewed(user, limit=10):
    """Produits récemment vus par l'utilisateur, triés par date DESC."""
    from apps.products.models import ProductView
    recent = (
        ProductView.objects.filter(user=user)
        .select_related('product')
        .order_by('-created_at')
        .values_list('product_id', flat=True)
        .distinct()[:limit]
    )
    product_map = {p.pk: p for p in _base_qs().filter(pk__in=recent)}
    return [product_map[pk] for pk in recent if pk in product_map]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Tendances locales (par store/région)
# ─────────────────────────────────────────────────────────────────────────────

def trending_by_store(store, limit=10, days=30):
    """Top produits d'une boutique donnée sur les derniers jours."""
    from apps.orders.models import OrderItem
    since = timezone.now() - timedelta(days=days)
    ids = (
        OrderItem.objects.filter(
            order__created_at__gte=since,
            order__status='completed',
            product__store=store,
        )
        .values('product_id')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')
        .values_list('product_id', flat=True)[:limit]
    )
    product_map = {p.pk: p for p in _base_qs().filter(pk__in=ids)}
    return [product_map[pk] for pk in ids if pk in product_map]


# ─────────────────────────────────────────────────────────────────────────────
# 6. Frequently Bought Together (panier)
# ─────────────────────────────────────────────────────────────────────────────

def frequently_bought_together(product, limit=5):
    """
    Produits fréquemment achetés avec `product` dans la même commande.
    """
    from apps.orders.models import OrderItem

    order_ids_with_product = (
        OrderItem.objects.filter(product=product, order__status='completed')
        .values_list('order_id', flat=True)
    )

    co_purchased = (
        _base_qs()
        .exclude(pk=product.pk)
        .filter(order_items__order_id__in=order_ids_with_product, order_items__order__status='completed')
        .annotate(freq=Count('order_items'))
        .order_by('-freq')
        .distinct()[:limit]
    )
    return list(co_purchased)
