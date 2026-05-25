import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class FlutterwaveGateway:
    def __init__(self):
        self.secret_key = settings.FLUTTERWAVE_SECRET_KEY
        self.public_key = settings.FLUTTERWAVE_PUBLIC_KEY
        self.base_url = settings.FLUTTERWAVE_BASE_URL

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
        }

    def initiate_payment(self, payment):
        order = payment.order
        address = order.shipping_address
        payload = {
            'tx_ref': payment.reference,
            'amount': str(payment.amount),
            'currency': payment.currency,
            'redirect_url': f'{settings.FRONTEND_URL}/orders/{order.order_number}?payment=success',
            'customer': {
                'email': order.user.email,
                'name': address.get('full_name', ''),
                'phonenumber': address.get('phone', ''),
            },
            'customizations': {
                'title': 'Dooya Marketplace',
                'description': f'Commande #{order.order_number}',
            },
            'meta': {
                'reference': payment.reference,
                'order_number': order.order_number,
            },
        }
        try:
            response = requests.post(f'{self.base_url}/payments', json=payload, headers=self._headers(), timeout=30)
            response.raise_for_status()
            data = response.json()
            if data.get('status') == 'success':
                return {
                    'payment_url': data['data']['link'],
                    'transaction_id': payment.reference,
                }
            raise Exception(f"Flutterwave error: {data.get('message')}")
        except Exception as e:
            logger.error(f"Flutterwave initiate error: {e}")
            raise

    def verify_payment(self, transaction_id):
        try:
            response = requests.get(
                f'{self.base_url}/transactions/{transaction_id}/verify',
                headers=self._headers(),
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            if data.get('status') == 'success' and data.get('data', {}).get('status') == 'successful':
                return {
                    'status': 'success',
                    'amount': data['data'].get('amount'),
                    'transaction_id': transaction_id,
                    'raw': data,
                }
            return {'status': 'failed', 'raw': data}
        except Exception as e:
            logger.error(f"Flutterwave verify error: {e}")
            return {'status': 'failed', 'error': str(e)}

    def process_webhook(self, data):
        from apps.payments.models import Payment
        from django.utils import timezone
        if data.get('event') != 'charge.completed':
            return None
        flw_tx_id = data.get('data', {}).get('id')
        meta = data.get('data', {}).get('meta', {})
        reference = meta.get('reference')
        if not reference:
            return None
        try:
            payment = Payment.objects.get(reference=reference)
        except Payment.DoesNotExist:
            return None
        result = self.verify_payment(flw_tx_id)
        if result['status'] == 'success':
            payment.status = 'success'
            payment.transaction_id = str(flw_tx_id)
            payment.paid_at = timezone.now()
            payment.save(update_fields=['status', 'transaction_id', 'paid_at'])
            payment.order.payment_status = 'paid'
            payment.order.status = 'confirmed'
            payment.order.save(update_fields=['payment_status', 'status'])
        else:
            payment.status = 'failed'
            payment.save(update_fields=['status'])
        return payment
