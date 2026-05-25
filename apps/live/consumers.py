import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class LiveSessionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time live shopping interaction.

    URL: ws://host/ws/live/<room_id>/

    Events client → server:
        join            { token? }
        leave           {}
        comment         { content, type: 'comment'|'like'|'love'|'fire'|'clap' }
        pin_comment     { comment_id }          host only
        feature_product { live_product_id }      host only

    Events server → client (broadcast):
        viewer_count    { count }
        new_comment     { id, user_name, user_avatar, content, type, is_pinned, created_at }
        product_featured { live_product }
        order_placed    { order_number, product_name, user_name }
        session_started {}
        session_ended   {}
        error           { message }
    """

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.group_name = f'live_{self.room_id}'
        self.session = await self._get_session(self.room_id)

        if not self.session:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Enregistrer le spectateur
        user = self.scope.get('user')
        self.viewer = await self._create_viewer(user)
        await self._increment_viewer_count()

        count = await self._get_viewer_count()
        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'viewer_count_update', 'count': count}
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'viewer') and self.viewer:
            await self._mark_viewer_left()

        await self._decrement_viewer_count()
        count = await self._get_viewer_count()
        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'viewer_count_update', 'count': count}
        )
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        event_type = data.get('type')
        user = self.scope.get('user')

        if event_type == 'comment':
            await self._handle_comment(user, data)
        elif event_type == 'pin_comment':
            await self._handle_pin_comment(user, data)
        elif event_type == 'feature_product':
            await self._handle_feature_product(user, data)

    # ── Handlers ──────────────────────────────────────────────────────────────

    async def _handle_comment(self, user, data):
        content = data.get('content', '').strip()
        comment_type = data.get('comment_type', 'comment')
        if not content and comment_type == 'comment':
            return

        comment = await self._save_comment(user, content, comment_type)
        if not comment:
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'broadcast_comment',
                'comment': {
                    'id': comment['id'],
                    'user_name': comment['user_name'],
                    'content': content,
                    'comment_type': comment_type,
                    'is_pinned': False,
                    'created_at': comment['created_at'],
                }
            }
        )

    async def _handle_pin_comment(self, user, data):
        if not await self._is_session_host(user):
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'Permission refusée.'}))
            return
        comment_id = data.get('comment_id')
        await self._pin_comment(comment_id)
        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'comment_pinned', 'comment_id': comment_id}
        )

    async def _handle_feature_product(self, user, data):
        if not await self._is_session_host(user):
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'Permission refusée.'}))
            return
        live_product_id = data.get('live_product_id')
        product_data = await self._feature_product(live_product_id)
        if product_data:
            await self.channel_layer.group_send(
                self.group_name,
                {'type': 'product_featured_event', 'live_product': product_data}
            )

    # ── Channel layer event handlers (broadcast to WebSocket) ─────────────────

    async def viewer_count_update(self, event):
        await self.send(text_data=json.dumps({'type': 'viewer_count', 'count': event['count']}))

    async def broadcast_comment(self, event):
        await self.send(text_data=json.dumps({'type': 'new_comment', **event['comment']}))

    async def comment_pinned(self, event):
        await self.send(text_data=json.dumps({'type': 'comment_pinned', 'comment_id': event['comment_id']}))

    async def product_featured_event(self, event):
        await self.send(text_data=json.dumps({'type': 'product_featured', 'live_product': event['live_product']}))

    async def order_placed_event(self, event):
        await self.send(text_data=json.dumps({'type': 'order_placed', **event['order_data']}))

    async def session_status_event(self, event):
        await self.send(text_data=json.dumps({'type': event['status']}))

    # ── DB helpers ────────────────────────────────────────────────────────────

    @database_sync_to_async
    def _get_session(self, room_id):
        from .models import LiveSession
        try:
            return LiveSession.objects.get(room_id=room_id)
        except LiveSession.DoesNotExist:
            return None

    @database_sync_to_async
    def _create_viewer(self, user):
        from .models import LiveViewer
        viewer = LiveViewer.objects.create(
            session=self.session,
            user=user if user and user.is_authenticated else None,
        )
        return viewer

    @database_sync_to_async
    def _mark_viewer_left(self):
        from .models import LiveViewer
        LiveViewer.objects.filter(pk=self.viewer.pk).update(
            left_at=timezone.now(), is_active=False
        )

    @database_sync_to_async
    def _increment_viewer_count(self):
        from .models import LiveSession
        from django.db.models import F
        LiveSession.objects.filter(pk=self.session.pk).update(
            viewer_count=F('viewer_count') + 1
        )
        self.session.refresh_from_db()
        if self.session.viewer_count > self.session.peak_viewer_count:
            LiveSession.objects.filter(pk=self.session.pk).update(
                peak_viewer_count=self.session.viewer_count
            )

    @database_sync_to_async
    def _decrement_viewer_count(self):
        from .models import LiveSession
        from django.db.models import F
        LiveSession.objects.filter(pk=self.session.pk).update(
            viewer_count=F('viewer_count') - 1
        )

    @database_sync_to_async
    def _get_viewer_count(self):
        from .models import LiveSession
        return LiveSession.objects.filter(pk=self.session.pk).values_list('viewer_count', flat=True).first() or 0

    @database_sync_to_async
    def _save_comment(self, user, content, comment_type):
        from .models import LiveComment
        comment = LiveComment.objects.create(
            session=self.session,
            user=user if user and user.is_authenticated else None,
            content=content,
            comment_type=comment_type,
        )
        user_name = user.get_full_name() if user and user.is_authenticated else 'Anonyme'
        return {'id': comment.pk, 'user_name': user_name, 'created_at': comment.created_at.isoformat()}

    @database_sync_to_async
    def _is_session_host(self, user):
        if not user or not user.is_authenticated:
            return False
        return self.session.host_id == user.pk or user.is_staff

    @database_sync_to_async
    def _pin_comment(self, comment_id):
        from .models import LiveComment
        LiveComment.objects.filter(session=self.session, pk=comment_id).update(is_pinned=True)

    @database_sync_to_async
    def _feature_product(self, live_product_id):
        from .models import LiveProduct
        try:
            lp = LiveProduct.objects.select_related('product').get(pk=live_product_id, session=self.session)
            lp.is_featured = True
            lp.save()
            return {'id': lp.pk, 'product_name': lp.product.name}
        except LiveProduct.DoesNotExist:
            return None
