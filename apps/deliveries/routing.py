from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/delivery/(?P<tracking_number>[A-Z0-9]+)/$', consumers.DeliveryTrackingConsumer.as_asgi()),
]
