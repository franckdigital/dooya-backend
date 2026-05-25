import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class PayDunyaGateway:
    def __init__(self):
        self.master_key = settings.PAYDUNYA_MASTER_KEY
        self.private_key = settings.PAYDUNYA_PRIVATE_KEY
        self.token = settings.PAYDUNYA_TOKEN
        self.base_url = settings.PAYDUNYA_BASE_URL

    def _headers(self):
        return {
            'PAYDUNYA-MASTER-KEY': self.master_key,
            'PAYDUNYA-PRIVATE-KEY': self.private_key,
            'PAYDUNYA-TOKEN': self.token,
            'Content-Type': 'application/json',
        }

    def initiate_payment(self, payment):
        order = payment.order
        payload = {
            'invoice': {
                'total_amount': int(payment.amount),
                'description': f'Commande #{order.order_number}',
            },
            'store': {
                'name': 'Dooya',
            },
            'actions': {
                'cancel_url': f'{settings.FRONTEND_URL}/orders/{order.order_number}',
                'return_url': f'{settings.FRONTEND_URL}/orders/{order.order_number}?payment=success',
                'callback_url': f'{settings.SITE_URL}/api/payments/webhook/paydunya/',
            },
            'custom_data': {
                'reference': payment.reference,
                'order_number': order.order_number,
            },
        }
        try:
            response = requests.post(f'{self.base_url}/checkout-invoice/create', json=payload, headers=self._headers(), timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('response_code') == '00':
                return {
                    'payment_url': data['response_text'],
                    'transaction_id': data.get('token'),
                }
            raise Exception(f"PayDunya error: {data.get('response_text')}")
        except Exception as e:
            logger.error(f"PayDunya initiate error: {e}")
            raise

    def verify_payment(self, transaction_id):
        try:
            response = requests.get(
                f'{self.base_url}/checkout-invoice/confirm/{transaction_id}',
                headers=self._headers(),
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            if data.get('response_code') == '00' and data.get('status') == 'completed':
                return {
                    'status': 'success',
                    'amount': data.get('invoice', {}).get('total_amount'),
                    'transaction_id': transaction_id,
                    'raw': data,
                }
            return {'status': 'failed', 'raw': data}
        except Exception as e:
            logger.error(f"PayDunya verify error: {e}")
            return {'status': 'failed', 'error': str(e)}

    def process_webhook(self, data):
        from apps.payments.models import Payment
        from django.utils import timezone
        token = data.get('data', {}).get('invoice', {}).get('token')
        if not token:
            return None
        result = self.verify_payment(token)
        custom = data.get('custom_data', {})
        reference = custom.get('reference')
        if not reference:
            return None
        try:
            payment = Payment.objects.get(reference=reference)
        except Payment.DoesNotExist:
            return None
        if result['status'] == 'success':
            payment.status = 'success'
            payment.transaction_id = token
            payment.paid_at = timezone.now()
            payment.save(update_fields=['status', 'transaction_id', 'paid_at'])
            payment.order.payment_status = 'paid'
            payment.order.status = 'confirmed'
            payment.order.save(update_fields=['payment_status', 'status'])
        else:
            payment.status = 'failed'
            payment.save(update_fields=['status'])
        return payment
