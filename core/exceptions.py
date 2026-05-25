from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        errors = response.data
        if isinstance(errors, dict):
            if 'detail' in errors:
                message = str(errors['detail'])
            elif 'non_field_errors' in errors:
                nfe = errors['non_field_errors']
                message = str(nfe[0]) if nfe else 'Erreur inconnue'
            else:
                # First field error found
                for v in errors.values():
                    if isinstance(v, list) and v:
                        message = str(v[0])
                        break
                else:
                    message = 'Erreur de validation'
        elif isinstance(errors, list):
            message = str(errors[0]) if errors else 'Erreur inconnue'
        else:
            message = str(errors)

        response.data = {
            'success': False,
            'message': message,
            'errors': errors,
            'status_code': response.status_code,
        }

    return response


class ServiceUnavailable(Exception):
    pass


class PaymentGatewayError(Exception):
    def __init__(self, message, gateway=None):
        self.gateway = gateway
        super().__init__(message)


class InsufficientStockError(Exception):
    def __init__(self, product_name, available):
        self.product_name = product_name
        self.available = available
        super().__init__(f"Stock insuffisant pour {product_name}: {available} disponible(s)")


class InsufficientBalanceError(Exception):
    pass
