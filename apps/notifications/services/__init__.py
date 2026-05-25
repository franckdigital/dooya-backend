import logging
from apps.notifications.models import Notification, NotificationPreference

logger = logging.getLogger(__name__)


def notify(user, notification_type, title, body, data=None, channels=None):
    prefs, _ = NotificationPreference.objects.get_or_create(user=user)
    if channels is None:
        channels = ['in_app']
    for channel in channels:
        Notification.objects.create(
            user=user,
            type=notification_type,
            title=title,
            body=body,
            data=data or {},
            channel=channel,
        )
        if channel == 'email':
            if notification_type == 'order' and not prefs.email_order:
                continue
            if notification_type == 'promo' and not prefs.email_promo:
                continue
            try:
                from apps.notifications.services.email import send_simple_email
                send_simple_email(user.email, title, body)
            except Exception as e:
                logger.error(f"Email notification error: {e}")

        elif channel == 'sms':
            if notification_type == 'order' and not prefs.sms_order:
                continue
            if notification_type == 'promo' and not prefs.sms_promo:
                continue
            if user.phone:
                try:
                    from apps.notifications.services.sms import send_sms
                    send_sms(user.phone, body)
                except Exception as e:
                    logger.error(f"SMS notification error: {e}")

        elif channel == 'whatsapp':
            if notification_type == 'order' and not prefs.whatsapp_order:
                continue
            if user.phone:
                try:
                    from apps.notifications.services.whatsapp import send_whatsapp
                    send_whatsapp(user.phone, body)
                except Exception as e:
                    logger.error(f"WhatsApp notification error: {e}")

        elif channel == 'push':
            if notification_type == 'order' and not prefs.push_order:
                continue
            if notification_type == 'promo' and not prefs.push_promo:
                continue
            try:
                from apps.notifications.services.push import send_push
                send_push(user, title, body, data)
            except Exception as e:
                logger.error(f"Push notification error: {e}")
