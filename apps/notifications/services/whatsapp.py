import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def send_whatsapp(phone, message, template_name=None, params=None):
    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER:
        logger.warning("WhatsApp not configured.")
        return False
    phone_clean = str(phone).replace('+', '').replace(' ', '')
    url = f"{settings.WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_NUMBER}/messages"
    headers = {
        'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}',
        'Content-Type': 'application/json',
    }
    if template_name:
        payload = {
            'messaging_product': 'whatsapp',
            'to': phone_clean,
            'type': 'template',
            'template': {
                'name': template_name,
                'language': {'code': 'fr'},
                'components': [
                    {
                        'type': 'body',
                        'parameters': [{'type': 'text', 'text': p} for p in (params or [])],
                    }
                ] if params else [],
            },
        }
    else:
        payload = {
            'messaging_product': 'whatsapp',
            'to': phone_clean,
            'type': 'text',
            'text': {'body': message},
        }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"WhatsApp sent to {phone}: {response.json()}")
        return True
    except Exception as e:
        logger.error(f"WhatsApp send error to {phone}: {e}")
        return False
