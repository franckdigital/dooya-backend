import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)


def send_email(to, subject, template, context):
    try:
        html_message = render_to_string(template, context)
        text_message = context.get('body', subject)
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to] if isinstance(to, str) else to,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email sent to {to}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Email send error to {to}: {e}")
        return False


def send_simple_email(to, subject, body):
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to] if isinstance(to, str) else to,
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Email send error to {to}: {e}")
        return False
