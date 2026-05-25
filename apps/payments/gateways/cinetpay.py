import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class CinetPayGateway:
    def __init__(self):
        self.api_key = settings.CINETPAY_API_KEY
        self.site_id = settings.CINETPAY_SITE_ID
        self.base_url = settings.CINETPAY_BASE_URL

    def initiate_payment(self, payment):
        order = payment.order
        payload = {
            'apikey': self.api_key,
            'site_id': self.site_id,
            'transaction_id': payment.reference,
            'amount': int(payment.amount),
            'currency': payment.currency,
            'description': f'Commande #{order.order_number}',
            'customer_name': order.shipping_address.get('full_name', ''),
            'customer_email': order.user.email,
            'customer_phone_number': order.shipping_address.get('phone', ''),
            'notify_url': f'{settings.SITE_URL}/api/payments/webhook/cinetpay/',
            'return_url': f'{settings.FRONTEND_URL}/orders/{order.order_number}',
            'channels': 'ALL',
            'lang': 'fr',
        }
        try:
            response = requests.post(f'{self.base_url}/payment', json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('code') == '201':
                return {
                    'payment_url': data['data']['payment_url'],
                    'transaction_id': payment.reference,
                }
            raise Exception(f"CinetPay error: {data.get('message')}")
        except Exception as e:
            logger.error(f"CinetPay initiate error: {e}")
            raise

    def verify_payment(self, transaction_id):
        payload = {
            'apikey': self.api_key,
            'site_id': self.site_id,
            'transaction_id': transaction_id,
        }
        try:
            response = requests.post(f'{self.base_url}/payment/check', json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('code') == '00':
                return {
                    'status': 'success',
                    'amount': data['data'].get('amount'),
                    'transaction_id': transaction_id,
                    'raw': data,
                }
            return {'status': 'failed', 'raw': data}
        except Exception as e:
            logger.error(f"CinetPay verify error: {e}")
            return {'status': 'failed', 'error': str(e)}

    def process_webhook(self, data):
        from apps.payments.models import Payment
        from django.utils import timezone
        transaction_id = data.get('cpm_trans_id')
        if not transaction_id:
            return None
        try:
            payment = Payment.objects.get(reference=transaction_id)
        except Payment.DoesNotExist:
            return None
        result = self.verify_payment(transaction_id)
        if result['status'] == 'success':
            payment.status = 'success'
            payment.transaction_id = transaction_id
            payment.paid_at = timezone.now()
            payment.save(update_fields=['status', 'transaction_id', 'paid_at'])
            payment.order.payment_status = 'paid'
            payment.order.status = 'confirmed'
            payment.order.save(update_fields=['payment_status', 'status'])
        else:
            payment.status = 'failed'
            payment.save(update_fields=['status'])
        return payment
