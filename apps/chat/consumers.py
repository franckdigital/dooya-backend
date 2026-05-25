import json
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close()
            return
        is_participant = await self.is_participant(user, self.conversation_id)
        if not is_participant:
            await self.close()
            return
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data.get('type', 'chat_message')
        user = self.scope['user']

        if event_type == 'chat_message':
            content = data.get('content', '')
            if not content:
                return
            message = await self.save_message(user, self.conversation_id, content)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': message['id'],
                    'content': message['content'],
                    'sender_id': user.pk,
                    'sender_name': user.full_name,
                    'created_at': message['created_at'],
                }
            )
        elif event_type == 'message_read':
            await self.mark_messages_read(user, self.conversation_id)
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'message_read', 'reader_id': user.pk}
            )
        elif event_type == 'user_typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'user_typing', 'user_id': user.pk, 'user_name': user.full_name}
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message_id': event['message_id'],
            'content': event['content'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'created_at': event['created_at'],
        }))

    async def message_read(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_read',
            'reader_id': event['reader_id'],
        }))

    async def user_typing(self, event):
        user = self.scope['user']
        if event['user_id'] != user.pk:
            await self.send(text_data=json.dumps({
                'type': 'user_typing',
                'user_id': event['user_id'],
                'user_name': event['user_name'],
            }))

    @database_sync_to_async
    def is_participant(self, user, conversation_id):
        from apps.chat.models import Conversation
        return Conversation.objects.filter(pk=conversation_id, participants=user).exists()

    @database_sync_to_async
    def save_message(self, user, conversation_id, content):
        from apps.chat.models import Conversation, Message
        conv = Conversation.objects.get(pk=conversation_id)
        msg = Message.objects.create(conversation=conv, sender=user, content=content)
        conv.updated_at = timezone.now()
        conv.save(update_fields=['updated_at'])
        return {
            'id': msg.pk,
            'content': msg.content,
            'created_at': msg.created_at.isoformat(),
        }

    @database_sync_to_async
    def mark_messages_read(self, user, conversation_id):
        from apps.chat.models import Message
        Message.objects.filter(
            conversation_id=conversation_id,
            is_read=False,
        ).exclude(sender=user).update(is_read=True, read_at=timezone.now())
