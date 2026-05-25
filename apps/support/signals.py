from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SupportTicket, Dispute, TicketMessage


def _notify_admins(notif_type, title, body, data):
    from django.contrib.auth import get_user_model
    from apps.notifications.models import Notification
    User = get_user_model()
    for admin in User.objects.filter(role='admin', is_active=True):
        Notification.objects.create(user=admin, type=notif_type, title=title, body=body, data=data)


@receiver(post_save, sender=SupportTicket)
def ticket_status_changed(sender, instance, created, **kwargs):
    from apps.notifications.models import Notification

    if created:
        Notification.objects.create(
            user=instance.user, type='ticket',
            title='Ticket support créé',
            body=f'Votre ticket {instance.reference} a été ouvert. Nous vous répondrons rapidement.',
            data={'ticket_id': instance.id, 'reference': instance.reference},
        )
        _notify_admins(
            notif_type='ticket',
            title=f'Nouveau ticket — {instance.reference}',
            body=f'{instance.user.get_full_name() or instance.user.email} a ouvert un ticket : « {instance.subject} ».',
            data={'ticket_id': instance.id, 'reference': instance.reference},
        )
    elif instance.status == 'resolved':
        Notification.objects.create(
            user=instance.user, type='ticket',
            title='Ticket résolu',
            body=f'Votre ticket {instance.reference} a été résolu.',
            data={'ticket_id': instance.id, 'reference': instance.reference},
        )


@receiver(post_save, sender=TicketMessage)
def ticket_message_added(sender, instance, created, **kwargs):
    if not created or instance.is_internal:
        return
    ticket = instance.ticket
    from apps.notifications.models import Notification

    if instance.sender and instance.sender == ticket.user:
        # Client replied → notify admins
        _notify_admins(
            notif_type='ticket',
            title=f'Nouveau message ticket — {ticket.reference}',
            body=f'{ticket.user.get_full_name() or ticket.user.email} a répondu sur le ticket {ticket.reference}.',
            data={'ticket_id': ticket.id, 'reference': ticket.reference},
        )
    elif instance.sender and instance.sender != ticket.user:
        # Staff replied → notify client
        Notification.objects.create(
            user=ticket.user, type='ticket',
            title=f'Réponse à votre ticket {ticket.reference}',
            body='L\'équipe Dooya vous a répondu sur votre ticket de support.',
            data={'ticket_id': ticket.id, 'reference': ticket.reference},
        )


@receiver(post_save, sender=Dispute)
def dispute_status_changed(sender, instance, created, **kwargs):
    from apps.notifications.models import Notification

    if created:
        Notification.objects.create(
            user=instance.complainant, type='dispute',
            title='Litige ouvert',
            body=f'Votre litige {instance.reference} a été ouvert et est en cours d\'examen.',
            data={'dispute_id': instance.id, 'reference': instance.reference},
        )
        _notify_admins(
            notif_type='dispute',
            title=f'Nouveau litige — {instance.reference}',
            body=f'{instance.complainant.get_full_name() or instance.complainant.email} a ouvert un litige : « {instance.subject} ».',
            data={'dispute_id': instance.id, 'reference': instance.reference},
        )
    elif instance.status in ('resolved_buyer', 'resolved_seller', 'resolved_partial', 'closed'):
        Notification.objects.create(
            user=instance.complainant, type='dispute',
            title='Décision rendue sur votre litige',
            body=f'Une décision a été rendue pour le litige {instance.reference}.',
            data={'dispute_id': instance.id, 'reference': instance.reference},
        )
