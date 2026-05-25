"""
Services qualité — orchestre retour produit, stock, inspections, fournisseurs.
Toutes les opérations critiques sont atomiques (transaction.atomic).
"""
from django.db import transaction
from django.utils import timezone


@transaction.atomic
def process_product_return(product_return, approved: bool, restock: bool,
                           resolution: str, resolution_notes: str = '',
                           refund_amount=None, processed_by=None,
                           create_replacement: bool = False,
                           replacement_product_id=None,
                           replacement_variant_id=None):
    """
    Traitement complet d'un retour produit :
      1. Mise à jour du statut
      2. Inspection qualité automatique
      3. Mise à jour du stock en temps réel
      4. Mise à jour du profil qualité produit
      5. Mise à jour du score qualité fournisseur si défaut fournisseur
      6. Remboursement wallet si applicable
      7. Notifications
    """
    from .models import QualityInspection, ProductQualityProfile
    from apps.inventory.services import record_movement

    now = timezone.now()
    pr = product_return

    if not approved:
        pr.status = 'rejected'
        pr.resolution = 'no_action'
        pr.resolution_notes = resolution_notes
        pr.processed_by = processed_by
        pr.processed_at = now
        pr.save()
        _notify_return_rejected(pr)
        return pr

    # ── 1. Créer l'inspection qualité si elle n'existe pas ───────────────────
    if not hasattr(pr, 'inspection') or pr.inspection is None:
        inspection = QualityInspection.objects.create(
            inspection_type='customer_return',
            product=pr.product,
            variant=pr.variant,
            supplier=pr.supplier,
            order_item=pr.order_item,
            product_return=pr,
            quantity_inspected=pr.quantity,
            quantity_failed=pr.quantity if pr.condition in ('defective', 'unusable', 'damaged') else 0,
            quantity_passed=pr.quantity if pr.condition in ('sealed', 'good', 'acceptable') else 0,
            result='failed' if pr.condition in ('defective', 'unusable') else 'partial',
            inspection_date=now.date(),
            inspector=processed_by,
            notes=resolution_notes,
        )
    else:
        inspection = pr.inspection

    # ── 2. Mise à jour du stock en temps réel ────────────────────────────────
    if not pr.stock_updated:
        if restock:
            record_movement(
                product=pr.product,
                quantity=pr.quantity,
                reason='return_customer',
                movement_type='return',
                variant=pr.variant,
                order=pr.order_item.order if pr.order_item else None,
                reference=pr.reference,
                notes=f'Retour client approuvé — {pr.reason}',
                performed_by=processed_by,
            )
            pr.restock = True
            new_status_after_stock = 'restocked'
        else:
            # Mise au rebut : sortie stock avec raison 'loss'
            record_movement(
                product=pr.product,
                quantity=-pr.quantity,
                reason='loss',
                movement_type='out',
                variant=pr.variant,
                reference=pr.reference,
                notes=f'Mise au rebut — retour {pr.reference} ({pr.condition})',
                performed_by=processed_by,
            )
            pr.restock = False
            new_status_after_stock = 'disposed'

        pr.stock_updated = True

    # ── 3. Profil qualité produit ─────────────────────────────────────────────
    _update_product_quality_profile(pr.product, pr.quantity, pr.condition in ('defective', 'unusable'))

    # ── 4. Score fournisseur si défaut origine fournisseur ───────────────────
    if pr.reason in ('defective', 'quality_issue', 'supplier_defect') and pr.supplier:
        _update_supplier_quality_score(pr.supplier, pr.quantity)

    # ── 5. Résolution ────────────────────────────────────────────────────────
    pr.resolution = resolution
    pr.resolution_notes = resolution_notes
    pr.processed_by = processed_by
    pr.processed_at = now

    if resolution in ('refund_wallet', 'refund_original', 'partial_refund') and refund_amount:
        pr.refund_amount = refund_amount
        pr.refunded_at = now
        if resolution == 'refund_wallet':
            _refund_to_wallet(pr, refund_amount)
        pr.status = 'refunded'
    elif resolution == 'replacement' or create_replacement:
        pr.status = 'replacement_pending'
        if replacement_product_id:
            from apps.products.models import Product, ProductVariant
            pr.replacement_product_id = replacement_product_id
            if replacement_variant_id:
                pr.replacement_variant_id = replacement_variant_id
    elif resolution == 'store_credit':
        _issue_store_credit(pr, refund_amount or pr.refund_amount or 0)
        pr.status = 'completed'
    else:
        pr.status = new_status_after_stock

    pr.save()
    _notify_return_approved(pr)
    return pr


def _update_product_quality_profile(product, qty, is_defective):
    from .models import ProductQualityProfile
    profile, _ = ProductQualityProfile.objects.get_or_create(product=product)
    profile.total_units_inspected += qty
    if is_defective:
        profile.total_units_defective += qty
    profile.total_returns += qty
    profile.recalculate()


def _update_supplier_quality_score(supplier, defective_qty):
    """Diminue le score qualité fournisseur proportionnellement aux défauts."""
    try:
        # Pénalité : -0.5 point par unité défectueuse, minimum 0
        penalty = min(defective_qty * 0.5, 10)
        supplier.quality_score = max(0, float(supplier.quality_score) - penalty)
        # Recalculer le rating
        score = float(supplier.quality_score)
        if score >= 95:
            supplier.quality_rating = 'A'
        elif score >= 80:
            supplier.quality_rating = 'B'
        elif score >= 60:
            supplier.quality_rating = 'C'
        elif score >= 40:
            supplier.quality_rating = 'D'
        else:
            supplier.quality_rating = 'F'
        supplier.save(update_fields=['quality_score', 'quality_rating'])
    except Exception:
        pass


def _refund_to_wallet(pr, amount):
    try:
        from apps.wallets.models import Wallet
        wallet, _ = Wallet.objects.get_or_create(user=pr.requested_by)
        wallet.credit(
            amount=amount,
            description=f'Remboursement retour {pr.reference}',
            ref=pr.reference,
        )
    except Exception:
        pass


def _issue_store_credit(pr, amount):
    """Crée un avoir en portefeuille avec catégorie 'refund'."""
    _refund_to_wallet(pr, amount)


def _notify_return_approved(pr):
    try:
        from apps.notifications.models import Notification
        Notification.objects.create(
            user=pr.requested_by,
            type='system',
            title='Retour approuvé',
            body=(
                f'Votre retour {pr.reference} a été approuvé. '
                f'Résolution : {pr.get_resolution_display()}.'
            ),
            data={'return_id': pr.id, 'reference': pr.reference},
        )
    except Exception:
        pass


def _notify_return_rejected(pr):
    try:
        from apps.notifications.models import Notification
        Notification.objects.create(
            user=pr.requested_by,
            type='system',
            title='Retour rejeté',
            body=(
                f'Votre retour {pr.reference} n\'a pas pu être approuvé. '
                f'Motif : {pr.resolution_notes or "non précisé"}.'
            ),
            data={'return_id': pr.id, 'reference': pr.reference},
        )
    except Exception:
        pass


def create_return_from_sav(sav_request, processed_by=None):
    """
    Crée automatiquement un ProductReturn depuis une SavRequest approuvée.
    Appelé par le signal sav.signals.
    """
    from .models import ProductReturn
    if ProductReturn.objects.filter(sav_request=sav_request).exists():
        return None

    pr = ProductReturn.objects.create(
        source='customer',
        requested_by=sav_request.user,
        product=sav_request.order_item.product,
        variant=sav_request.order_item.variant,
        quantity=1,
        order_item=sav_request.order_item,
        sav_request=sav_request,
        reason=sav_request.reason,
        description=sav_request.description or sav_request.get_reason_display(),
        condition='defective',
        processed_by=processed_by,
    )
    # Copier les images du SAV vers le retour
    for sav_img in sav_request.images.all():
        from .models import ProductReturnImage
        ProductReturnImage.objects.create(
            product_return=pr,
            image=sav_img.image,
            order=sav_img.order,
            uploaded_by=sav_request.user,
        )
    return pr
