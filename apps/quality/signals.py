from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

_return_prev_status = {}


def _notify_admins_return(title, body, data):
    from django.contrib.auth import get_user_model
    from apps.notifications.models import Notification
    User = get_user_model()
    for admin in User.objects.filter(role='admin', is_active=True):
        Notification.objects.create(user=admin, type='return', title=title, body=body, data=data)


@receiver(pre_save, sender='quality.ProductReturn')
def cache_return_prev_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            _return_prev_status[instance.pk] = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender='quality.ProductReturn')
def notify_on_return_changed(sender, instance, created, **kwargs):
    from apps.notifications.models import Notification

    if created:
        Notification.objects.create(
            user=instance.requested_by, type='return',
            title='Demande de retour reçue',
            body=f'Votre demande de retour {instance.reference} a bien été enregistrée.',
            data={'return_id': instance.id, 'reference': instance.reference},
        )
        _notify_admins_return(
            title=f'Nouveau retour produit — {instance.reference}',
            body=f'{instance.requested_by.get_full_name() or instance.requested_by.email} a soumis une demande de retour.',
            data={'return_id': instance.id, 'reference': instance.reference},
        )
        return

    prev = _return_prev_status.pop(instance.pk, None)
    if not prev or prev == instance.status:
        return

    STATUS_MSG = {
        'approved':             'Votre retour a été approuvé. Veuillez nous renvoyer le colis.',
        'rejected':             'Votre demande de retour a été refusée.',
        'received':             'Nous avons bien reçu votre colis retourné.',
        'under_inspection':     'Votre colis est en cours d\'inspection qualité.',
        'replacement_pending':  'Votre remplacement est en cours de préparation.',
        'replacement_sent':     'Votre colis de remplacement a été expédié !',
        'refunded':             'Votre remboursement a été effectué.',
        'restocked':            'Votre retour a été traité et remis en stock.',
        'completed':            'Votre demande de retour est maintenant clôturée.',
    }
    msg = STATUS_MSG.get(instance.status)
    if msg:
        Notification.objects.create(
            user=instance.requested_by, type='return',
            title=f'Retour {instance.reference} — mise à jour',
            body=msg,
            data={'return_id': instance.id, 'reference': instance.reference, 'status': instance.status},
        )


@receiver(post_save, sender='sav.SavRequest')
def create_return_on_sav_approval(sender, instance, created, **kwargs):
    if created:
        return
    if instance.type == 'return' and instance.status == 'approved':
        try:
            from apps.quality.services import create_return_from_sav
            create_return_from_sav(instance, processed_by=instance.resolved_by)
        except Exception:
            pass


@receiver(post_save, sender='quality.QualityInspection')
def update_product_profile_on_inspection(sender, instance, created, **kwargs):
    if instance.result not in ('passed', 'failed', 'partial'):
        return
    try:
        from .models import ProductQualityProfile
        profile, _ = ProductQualityProfile.objects.get_or_create(product=instance.product)
        profile.total_units_inspected += instance.quantity_inspected
        profile.total_units_defective += instance.quantity_failed
        if instance.inspection_date:
            profile.last_inspection_date = instance.inspection_date
        profile.recalculate()

        if profile.grade == 'F':
            from apps.notifications.models import Notification
            store_owner = instance.product.store.owner
            Notification.objects.create(
                user=store_owner, type='system',
                title='Alerte qualité critique',
                body=(
                    f'Le produit "{instance.product.name}" a atteint le grade F (Défectueux). '
                    f'Score qualité : {profile.quality_score}%.'
                ),
                data={'product_id': instance.product.id, 'grade': 'F'},
            )
    except Exception:
        pass


@receiver(post_save, sender='quality.SupplierQualityNotice')
def notify_on_quality_notice_sent(sender, instance, created, **kwargs):
    if not created and instance.status == 'sent':
        try:
            from apps.notifications.models import Notification
            from django.contrib.auth import get_user_model
            User = get_user_model()
            for admin in User.objects.filter(role='admin', is_active=True):
                Notification.objects.create(
                    user=admin, type='system',
                    title='Avis non-conformité envoyé',
                    body=f'Avis {instance.reference} envoyé à {instance.supplier.name}.',
                    data={'notice_id': instance.id},
                )
        except Exception:
            pass
