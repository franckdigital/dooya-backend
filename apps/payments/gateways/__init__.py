from .cinetpay import CinetPayGateway
from .paydunya import PayDunyaGateway
from .flutterwave import FlutterwaveGateway


def get_gateway(name):
    gateways = {
        'cinetpay': CinetPayGateway,
        'paydunya': PayDunyaGateway,
        'flutterwave': FlutterwaveGateway,
    }
    cls = gateways.get(name)
    if not cls:
        raise ValueError(f"Passerelle de paiement inconnue: {name}")
    return cls()
