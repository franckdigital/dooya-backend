import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class DeliveryTrackingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket pour le suivi GPS en temps réel d'une livraison.

    URL: ws://host/ws/delivery/<tracking_number>/

    Abonnement public (client / vendeur) — lecture seule.
    Le livreur met à jour la position via l'API REST PATCH /delivery/<pk>/gps/
    qui envoie ensuite un event 'gps_update' dans ce groupe.

    Events serveur → client:
        gps_update   { latitude, longitude, tracking_number }
        status_update { status, location, note }
    """

    async def connect(self):
        self.tracking_number = self.scope['url_route']['kwargs']['tracking_number']
        self.group_name = f'delivery_{self.tracking_number}'

        exists = await self._delivery_exists(self.tracking_number)
        if not exists:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Envoyer position actuelle à la connexion
        position = await self._get_current_position(self.tracking_number)
        if position:
            await self.send(text_data=json.dumps({'type': 'gps_update', **position}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # Les clients ne peuvent qu'écouter, pas envoyer de données GPS
        pass

    # ── Channel layer event handlers ──────────────────────────────────────────

    async def gps_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'gps_update',
            'latitude': event['latitude'],
            'longitude': event['longitude'],
            'tracking_number': event['tracking_number'],
        }))

    async def status_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'status': event['status'],
            'location': event.get('location', ''),
            'note': event.get('note', ''),
        }))

    # ── DB helpers ────────────────────────────────────────────────────────────

    @database_sync_to_async
    def _delivery_exists(self, tracking_number):
        from .models import Delivery
        return Delivery.objects.filter(tracking_number=tracking_number).exists()

    @database_sync_to_async
    def _get_current_position(self, tracking_number):
        from .models import Delivery
        d = Delivery.objects.filter(tracking_number=tracking_number).values(
            'current_latitude', 'current_longitude'
        ).first()
        if d and d['current_latitude']:
            return {
                'latitude': str(d['current_latitude']),
                'longitude': str(d['current_longitude']),
                'tracking_number': tracking_number,
            }
        return None
