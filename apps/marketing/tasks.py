from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(name='marketing.send_campaign')
def send_campaign_task(campaign_id: int):
    """Envoie une campagne à tous ses destinataires (batch Celery)."""
    from django.utils import timezone
    from .models import Campaign, CampaignRecipient
    from .services import _resolve_audience, _send_to_recipient

    try:
        campaign = Campaign.objects.get(pk=campaign_id)
    except Campaign.DoesNotExist:
        return

    if campaign.status not in ('scheduled', 'draft'):
        return

    campaign.status = 'sending'
    campaign.save(update_fields=['status'])

    users = _resolve_audience(campaign)
    campaign.total_recipients = len(users)
    campaign.save(update_fields=['total_recipients'])

    sent = failed = 0
    for user in users:
        recipient, _ = CampaignRecipient.objects.get_or_create(
            campaign=campaign, user=user,
            defaults={'status': 'pending'}
        )
        if recipient.status in ('sent', 'opened', 'clicked'):
            continue

        success = _send_to_recipient(campaign, user)
        if success:
            recipient.status = 'sent'
            recipient.sent_at = timezone.now()
            sent += 1
        else:
            recipient.status = 'failed'
            failed += 1
        recipient.save(update_fields=['status', 'sent_at'])

    campaign.status = 'sent'
    campaign.sent_at = timezone.now()
    campaign.sent_count = sent
    campaign.failed_count = failed
    campaign.save(update_fields=['status', 'sent_at', 'sent_count', 'failed_count'])

    logger.info('Campaign %s sent: %d success, %d failed', campaign.name, sent, failed)
    return {'sent': sent, 'failed': failed}


@shared_task(name='marketing.check_abandoned_carts')
def check_abandoned_carts_task():
    """
    Détecte les paniers non convertis depuis X heures et crée/met à jour
    des enregistrements AbandonedCartReminder.
    Déclenche les relances selon le calendrier :
      - Relance 1 : 1h après abandon
      - Relance 2 : 24h après abandon
      - Relance 3 : 72h après abandon
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.cart.models import Cart
    from apps.users.models import User
    from .models import AbandonedCartReminder, Unsubscribe
    from .services import _send_abandoned_cart_reminder

    now = timezone.now()
    reminder_schedule = [1, 24, 72]  # heures

    # Paniers non vides, non convertis, propriétaires authentifiés
    carts = (
        Cart.objects.filter(user__isnull=False, items__isnull=False)
        .select_related('user')
        .distinct()
    )

    unsubscribed_ids = set(
        Unsubscribe.objects.filter(channel__in=['email', 'all']).values_list('user_id', flat=True)
    )

    for cart in carts:
        if cart.user_id in unsubscribed_ids:
            continue

        # Vérifier si le client a passé une commande depuis le dernier update du panier
        from apps.orders.models import Order
        has_recent_order = Order.objects.filter(
            user=cart.user,
            created_at__gte=cart.updated_at,
            status__in=['pending', 'confirmed', 'shipped', 'delivered', 'completed'],
        ).exists()

        if has_recent_order:
            # Marquer comme converti si un reminder existe
            AbandonedCartReminder.objects.filter(cart=cart, status='pending').update(
                status='converted', converted_at=now
            )
            continue

        reminder, created = AbandonedCartReminder.objects.get_or_create(
            cart=cart, user=cart.user,
            defaults={'cart_total': sum(i.total_price for i in cart.items.all())}
        )

        if reminder.status in ('converted', 'expired'):
            continue

        hours_since_update = (now - cart.updated_at).total_seconds() / 3600
        next_reminder_idx = reminder.reminder_count  # 0-based

        if next_reminder_idx >= len(reminder_schedule):
            reminder.status = 'expired'
            reminder.save(update_fields=['status'])
            continue

        threshold = reminder_schedule[next_reminder_idx]
        if hours_since_update >= threshold:
            _send_abandoned_cart_reminder(reminder)
            reminder.reminder_count += 1
            reminder.last_sent_at = now
            reminder.status = 'sent'
            reminder.save(update_fields=['reminder_count', 'last_sent_at', 'status'])


@shared_task(name='marketing.schedule_due_campaigns')
def schedule_due_campaigns_task():
    """Déclenche les campagnes dont la date d'envoi est passée."""
    from django.utils import timezone
    from .models import Campaign
    due = Campaign.objects.filter(status='scheduled', scheduled_at__lte=timezone.now())
    for campaign in due:
        send_campaign_task.delay(campaign.pk)
