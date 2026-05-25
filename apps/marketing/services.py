"""
Services marketing : résolution d'audience, envoi multi-canal, relances panier.
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def _resolve_audience(campaign):
    """Retourne la liste d'utilisateurs ciblés par la campagne."""
    from apps.users.models import User
    from apps.orders.models import Order
    from datetime import timedelta

    now = timezone.now()

    if campaign.audience == 'all':
        return list(User.objects.filter(is_active=True))

    elif campaign.audience == 'customers':
        user_ids = Order.objects.filter(
            status__in=['completed', 'delivered']
        ).values_list('user_id', flat=True).distinct()
        return list(User.objects.filter(pk__in=user_ids, is_active=True))

    elif campaign.audience == 'vendors':
        return list(User.objects.filter(is_active=True, store__isnull=False))

    elif campaign.audience == 'inactive':
        cutoff = now - timedelta(days=30)
        active_ids = Order.objects.filter(
            created_at__gte=cutoff
        ).values_list('user_id', flat=True).distinct()
        return list(User.objects.filter(is_active=True).exclude(pk__in=active_ids))

    elif campaign.audience == 'new':
        cutoff = now - timedelta(days=7)
        return list(User.objects.filter(is_active=True, date_joined__gte=cutoff))

    return list(User.objects.filter(is_active=True))


def _send_to_recipient(campaign, user) -> bool:
    """Envoie un message à un utilisateur selon le canal de la campagne."""
    try:
        if campaign.channel == 'email':
            return _send_email(campaign, user)
        elif campaign.channel == 'sms':
            return _send_sms(campaign, user)
        elif campaign.channel == 'push':
            return _send_push(campaign, user)
        elif campaign.channel == 'whatsapp':
            return _send_whatsapp(campaign, user)
    except Exception as e:
        logger.warning('Failed to send campaign %s to %s: %s', campaign.pk, user.email, e)
    return False


def _send_email(campaign, user) -> bool:
    from apps.notifications.services.email import send_email
    return send_email(
        to=user.email,
        subject=campaign.subject or campaign.name,
        html_content=campaign.content,
    )


def _send_sms(campaign, user) -> bool:
    phone = getattr(user, 'phone_number', None)
    if not phone:
        return False
    from apps.notifications.services.sms import send_sms
    return send_sms(to=str(phone), message=campaign.content[:160])


def _send_push(campaign, user) -> bool:
    from apps.notifications.services.push import send_push_notification
    return send_push_notification(
        user=user,
        title=campaign.subject or campaign.name,
        body=campaign.content[:200],
        url=campaign.cta_url or '',
    )


def _send_whatsapp(campaign, user) -> bool:
    phone = getattr(user, 'phone_number', None)
    if not phone:
        return False
    from apps.notifications.services.whatsapp import send_whatsapp_message
    return send_whatsapp_message(to=str(phone), message=campaign.content[:1000])


def _send_abandoned_cart_reminder(reminder):
    """Envoie la relance panier via email et/ou push."""
    user = reminder.user
    cart = reminder.cart
    items = cart.items.select_related('product').all()
    item_list = ', '.join(i.product.name for i in items[:3])
    if items.count() > 3:
        item_list += f' et {items.count() - 3} autre(s)'

    subject = 'Vous avez oublié quelque chose !'
    body = (
        f'Bonjour {user.first_name or ""},\n\n'
        f'Votre panier contient encore : {item_list}.\n'
        f'Total estimé : {reminder.cart_total} FCFA.\n\n'
        'Finalisez votre commande avant que les stocks s\'épuisent !'
    )

    try:
        from apps.notifications.services.email import send_email
        send_email(to=user.email, subject=subject, html_content=body)
    except Exception as e:
        logger.warning('Abandoned cart email failed for %s: %s', user.email, e)

    try:
        from apps.notifications.services.push import send_push_notification
        send_push_notification(
            user=user,
            title='Votre panier vous attend !',
            body=f'{item_list} — {reminder.cart_total} FCFA',
        )
    except Exception:
        pass
