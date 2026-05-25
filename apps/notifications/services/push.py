import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

FCM_URL = 'https://fcm.googleapis.com/fcm/send'


def send_push(user, title, body, data=None):
    if not settings.FCM_SERVER_KEY:
        logger.warning("FCM not configured.")
        return False
    fcm_token = getattr(user, 'fcm_token', None)
    if not fcm_token:
        return False
    headers = {
        'Authorization': f'key={settings.FCM_SERVER_KEY}',
        'Content-Type': 'application/json',
    }
    payload = {
        'to': fcm_token,
        'notification': {
            'title': title,
            'body': body,
            'sound': 'default',
        },
        'data': data or {},
        'priority': 'high',
    }
    try:
        response = requests.post(FCM_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get('success'):
            logger.info(f"Push sent to {user.email}")
            return True
        logger.warning(f"Push failed for {user.email}: {result}")
        return False
    except Exception as e:
        logger.error(f"Push send error for {user.email}: {e}")
        return False
