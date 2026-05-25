from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SavRequest, SavMessage


def _notify_admins(title, body, data):
    from django.contrib.auth import get_user_model
    from apps.notifications.models import Notification
    User = get_user_model()
    for admin in User.objects.filter(role='admin', is_active=True):
        Notification.objects.create(user=admin, type='sav', title=title, body=body, data=data)


@receiver(post_save, sender=SavRequest)
def sav_status_changed(sender, instance, created, **kwargs):
    from apps.notifications.models import Notification

    if created:
        Notification.objects.create(
            user=instance.user, type='sav',
            title='Demande SAV reçue',
            body=f'Votre demande SAV {instance.reference} a bien été reçue et est en cours de traitement.',
            data={'sav_id': instance.id, 'reference': instance.reference},
        )
        _notify_admins(
            title=f'Nouvelle demande SAV — {instance.reference}',
            body=f'{instance.user.get_full_name() or instance.user.email} a soumis une demande SAV ({instance.get_type_display()}).',
            data={'sav_id': instance.id, 'reference': instance.reference},
        )
        return

    if instance.status == 'approved':
        Notification.objects.create(
            user=instance.user, type='sav',
            title='Demande SAV approuvée',
            body=f'Votre demande SAV {instance.reference} a été approuvée.',
            data={'sav_id': instance.id, 'reference': instance.reference},
        )
    elif instance.status == 'rejected':
        Notification.objects.create(
            user=instance.user, type='sav',
            title='Demande SAV rejetée',
            body=(
                f'Votre demande SAV {instance.reference} a été rejetée. '
                f'Raison : {instance.resolution_notes or "Non précisée"}'
            ),
            data={'sav_id': instance.id, 'reference': instance.reference},
        )
    elif instance.status == 'completed':
        Notification.objects.create(
            user=instance.user, type='sav',
            title='Demande SAV traitée',
            body=f'Votre demande SAV {instance.reference} a été traitée avec succès.',
            data={'sav_id': instance.id, 'reference': instance.reference},
        )
        if instance.refund_amount and instance.refund_method == 'wallet':
            try:
                from apps.wallets.models import Wallet, WalletTransaction
                wallet, _ = Wallet.objects.get_or_create(user=instance.user)
                wallet.balance += instance.refund_amount
                wallet.save(update_fields=['balance'])
                WalletTransaction.objects.create(
                    wallet=wallet, transaction_type='credit',
                    amount=instance.refund_amount,
                    description=f'Remboursement SAV {instance.reference}',
                    reference=instance.reference,
                )
            except Exception:
                pass


@receiver(post_save, sender=SavMessage)
def sav_message_created(sender, instance, created, **kwargs):
    if not created or instance.is_internal:
        return
    sav = instance.request
    from apps.notifications.models import Notification

    if instance.sender and instance.sender == sav.user:
        # Client sent a message → notify admins
        _notify_admins(
            title=f'Nouveau message SAV — {sav.reference}',
            body=f'{sav.user.get_full_name() or sav.user.email} a répondu sur le SAV {sav.reference}.',
            data={'sav_id': sav.id, 'reference': sav.reference},
        )
    elif instance.sender and instance.sender != sav.user:
        # Admin sent a message → notify client
        Notification.objects.create(
            user=sav.user, type='sav',
            title=f'Réponse sur votre SAV {sav.reference}',
            body='L\'équipe Dooya vous a répondu sur votre demande SAV.',
            data={'sav_id': sav.id, 'reference': sav.reference},
        )
