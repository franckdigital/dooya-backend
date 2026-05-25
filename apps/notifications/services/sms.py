import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def _send_via_twilio(phone, message):
    from twilio.rest import Client
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    msg = client.messages.create(
        body=message,
        from_=settings.TWILIO_PHONE_NUMBER,
        to=str(phone),
    )
    logger.info(f"SMS sent via Twilio to {phone}: {msg.sid}")
    return True


def _send_via_africastalking(phone, message):
    import africastalking
    africastalking.initialize(settings.AFRICASTALKING_USERNAME, settings.AFRICASTALKING_API_KEY)
    sms = africastalking.SMS
    response = sms.send(message, [str(phone)])
    logger.info(f"SMS sent via Africa's Talking to {phone}: {response}")
    return True


def send_sms(phone, message):
    if not phone or not message:
        return False
    if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
        try:
            return _send_via_twilio(phone, message)
        except Exception as e:
            logger.warning(f"Twilio SMS failed, trying Africa's Talking: {e}")
    if settings.AFRICASTALKING_USERNAME and settings.AFRICASTALKING_API_KEY:
        try:
            return _send_via_africastalking(phone, message)
        except Exception as e:
            logger.error(f"Africa's Talking SMS failed: {e}")
    logger.error(f"SMS could not be sent to {phone}: no provider configured.")
    return False
