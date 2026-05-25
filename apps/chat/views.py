from django.utils import timezone
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.pagination import StandardPagination
from core.permissions import IsAdmin, IsAdminOrCommercial
from .models import Conversation, Message, MessageReaction
from .serializers import ConversationSerializer, ConversationListSerializer, MessageSerializer, AdminConversationListSerializer


@extend_schema(tags=['chat'])
class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = Conversation.objects.filter(participants=request.user).prefetch_related('participants', 'messages').order_by('-updated_at')
        serializer = ConversationListSerializer(conversations, many=True, context={'request': request})
        return Response(serializer.data)


@extend_schema(tags=['chat'])
class ConversationCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        recipient_id = request.data.get('recipient_id')
        conv_type = request.data.get('type', 'customer_vendor')
        order_id = request.data.get('order_id')

        try:
            recipient = User.objects.get(pk=recipient_id)
        except User.DoesNotExist:
            return Response({'detail': 'Destinataire introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        existing = Conversation.objects.filter(participants=request.user).filter(participants=recipient).filter(type=conv_type).first()
        if existing:
            return Response(ConversationSerializer(existing, context={'request': request}).data)

        conv = Conversation.objects.create(type=conv_type)
        conv.participants.add(request.user, recipient)
        if order_id:
            from apps.orders.models import Order
            try:
                order = Order.objects.get(pk=order_id)
                conv.order = order
                conv.save(update_fields=['order'])
            except Order.DoesNotExist:
                pass
        return Response(ConversationSerializer(conv, context={'request': request}).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['chat'])
class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            conv = Conversation.objects.get(pk=pk, participants=request.user)
        except Conversation.DoesNotExist:
            return Response({'detail': 'Conversation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        paginator = StandardPagination()
        messages = conv.messages.all().select_related('sender').order_by('-created_at')
        page = paginator.paginate_queryset(messages, request)
        serializer = MessageSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


@extend_schema(tags=['chat'])
class MessageCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            conv = Conversation.objects.get(pk=pk, participants=request.user)
        except Conversation.DoesNotExist:
            return Response({'detail': 'Conversation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        content = request.data.get('content', '')
        msg_type = request.data.get('type', 'text')
        file = request.FILES.get('file')
        if not content and not file:
            return Response({'detail': 'Contenu ou fichier requis.'}, status=status.HTTP_400_BAD_REQUEST)
        message = Message.objects.create(
            conversation=conv,
            sender=request.user,
            content=content,
            type=msg_type,
            file=file,
        )
        conv.updated_at = timezone.now()
        conv.save(update_fields=['updated_at'])
        serializer = MessageSerializer(message, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['chat'])
class MessageReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            conv = Conversation.objects.get(pk=pk, participants=request.user)
        except Conversation.DoesNotExist:
            return Response({'detail': 'Conversation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        Message.objects.filter(conversation=conv, is_read=False).exclude(sender=request.user).update(
            is_read=True,
            read_at=timezone.now(),
        )
        return Response({'detail': 'Messages marqués comme lus.'})


@extend_schema(tags=['chat'])
class VoiceMessageView(APIView):
    """Envoi d'un message vocal (fichier audio multipart)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            conv = Conversation.objects.get(pk=pk, participants=request.user)
        except Conversation.DoesNotExist:
            return Response({'detail': 'Conversation introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response({'detail': 'Champ audio requis.'}, status=status.HTTP_400_BAD_REQUEST)

        duration = request.data.get('duration_seconds')
        waveform = request.data.get('waveform')  # JSON list optionnel

        message = Message.objects.create(
            conversation=conv,
            sender=request.user,
            type='audio',
            file=audio_file,
            audio_duration_seconds=int(duration) if duration else None,
            audio_waveform=waveform if isinstance(waveform, list) else None,
        )

        conv.updated_at = timezone.now()
        conv.save(update_fields=['updated_at'])

        # Transcription asynchrone optionnelle
        _transcribe_voice_message_async(message.pk, audio_file)

        return Response(MessageSerializer(message, context={'request': request}).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['chat-admin'])
class AdminConversationListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrCommercial]

    def get(self, request):
        conversations = Conversation.objects.all().prefetch_related('participants', 'messages').order_by('-updated_at')
        serializer = AdminConversationListSerializer(conversations, many=True, context={'request': request})
        return Response(serializer.data)


@extend_schema(tags=['chat-admin'])
class AdminConversationDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrCommercial]

    def get(self, request, pk):
        try:
            conv = Conversation.objects.get(pk=pk)
        except Conversation.DoesNotExist:
            return Response({'detail': 'Conversation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        paginator = StandardPagination()
        messages = conv.messages.all().select_related('sender').order_by('-created_at')
        page = paginator.paginate_queryset(messages, request)
        serializer = MessageSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


@extend_schema(tags=['chat-admin'])
class AdminMessageCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrCommercial]

    def post(self, request, pk):
        try:
            conv = Conversation.objects.get(pk=pk)
        except Conversation.DoesNotExist:
            return Response({'detail': 'Conversation introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        if not conv.participants.filter(pk=request.user.pk).exists():
            conv.participants.add(request.user)

        content = request.data.get('content', '')
        msg_type = request.data.get('type', 'text')
        file = request.FILES.get('file')
        if not content and not file:
            return Response({'detail': 'Contenu ou fichier requis.'}, status=status.HTTP_400_BAD_REQUEST)

        message = Message.objects.create(
            conversation=conv,
            sender=request.user,
            content=content,
            type=msg_type,
            file=file,
        )
        conv.updated_at = timezone.now()
        conv.save(update_fields=['updated_at'])
        return Response(MessageSerializer(message, context={'request': request}).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['chat-admin'])
class AdminMessageReadView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrCommercial]

    def post(self, request, pk):
        try:
            conv = Conversation.objects.get(pk=pk)
        except Conversation.DoesNotExist:
            return Response({'detail': 'Conversation introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        Message.objects.filter(conversation=conv, is_read=False).exclude(sender=request.user).update(
            is_read=True,
            read_at=timezone.now(),
        )
        return Response({'detail': 'Messages marqués comme lus.'})


def _transcribe_voice_message_async(message_id, audio_file):
    """Lance la transcription en arrière-plan si un service est configuré."""
    from django.conf import settings
    if not getattr(settings, 'GOOGLE_SPEECH_API_KEY', '') and not getattr(settings, 'USE_WHISPER', False):
        return
    try:
        from .tasks import transcribe_voice_message_task
        transcribe_voice_message_task.delay(message_id)
    except Exception:
        pass


@extend_schema(tags=['chat'])
class ConversationSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({'detail': 'Paramètre q requis.'}, status=status.HTTP_400_BAD_REQUEST)
        conversations = Conversation.objects.filter(
            participants=request.user,
            messages__content__icontains=query,
        ).distinct().prefetch_related('participants', 'messages')
        serializer = ConversationListSerializer(conversations, many=True, context={'request': request})
        return Response(serializer.data)
