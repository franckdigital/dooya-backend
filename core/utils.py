import uuid
import random
import string
import qrcode
import io
import base64
from django.http import JsonResponse
from django.utils.text import slugify


def generate_unique_slug(model_class, value, slug_field='slug'):
    slug = slugify(value)
    unique_slug = slug
    counter = 1
    while model_class.objects.filter(**{slug_field: unique_slug}).exists():
        unique_slug = f'{slug}-{counter}'
        counter += 1
    return unique_slug


def generate_order_number():
    prefix = 'DOO'
    random_part = ''.join(random.choices(string.digits, k=8))
    return f'{prefix}{random_part}'


def generate_tracking_number():
    return 'TRK' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))


def generate_reference():
    return str(uuid.uuid4()).replace('-', '').upper()[:16]


def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))


def generate_qr_code(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')


def axes_lockout_response(request, credentials, *args, **kwargs):
    return JsonResponse(
        {'success': False, 'message': 'Compte temporairement verrouillé suite à trop de tentatives échouées.'},
        status=403,
    )


def format_price(amount, currency='XOF'):
    return f'{int(amount):,} {currency}'.replace(',', ' ')


def calculate_commission(amount, rate):
    return round(amount * rate, 2)


def is_valid_phone(phone):
    import re
    pattern = r'^\+?[1-9]\d{7,14}$'
    return bool(re.match(pattern, phone.replace(' ', '')))
