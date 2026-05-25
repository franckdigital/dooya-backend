from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsAdmin
from core.pagination import StandardPagination
from .models import Notification, NotificationPreference
from .serializers import NotificationSerializer, NotificationPreferenceSerializer
from django.contrib.auth import get_user_model


@extend_schema(tags=['notifications'])
class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user, channel='in_app')
        is_read = self.request.query_params.get('is_read')
        notif_type = self.request.query_params.get('type')
        if is_read is not None:
            qs = qs.filter(is_read=is_read.lower() == 'true')
        if notif_type:
            qs = qs.filter(type=notif_type)
        return qs.order_by('-created_at')


@extend_schema(tags=['notifications'])
class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        notif_id = request.data.get('notification_id')
        mark_all = request.data.get('all', False)
        if mark_all:
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            return Response({'detail': 'Toutes les notifications marquées comme lues.'})
        if notif_id:
            try:
                notif = Notification.objects.get(pk=notif_id, user=request.user)
                notif.is_read = True
                notif.save(update_fields=['is_read'])
                return Response(NotificationSerializer(notif).data)
            except Notification.DoesNotExist:
                return Response({'detail': 'Notification introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'detail': 'notification_id ou all requis.'}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['notifications'])
class NotificationPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pref, _ = NotificationPreference.objects.get_or_create(user=request.user)
        return Response(NotificationPreferenceSerializer(pref).data)

    def patch(self, request):
        pref, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(pref, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['notifications'])
class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            user=request.user, is_read=False, channel='in_app'
        ).count()
        return Response({'unread_count': count})


@extend_schema(tags=['notifications'])
class AdminNotificationBroadcastView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        User = get_user_model()
        title = request.data.get('title', '')
        body = request.data.get('body', '')
        notif_type = request.data.get('type', 'system')
        role = request.data.get('role')
        channels = request.data.get('channels', ['in_app'])

        if not title or not body:
            return Response({'detail': 'title et body requis.'}, status=status.HTTP_400_BAD_REQUEST)

        users_qs = User.objects.filter(is_active=True)
        if role:
            users_qs = users_qs.filter(role=role)

        from .services import notify
        count = 0
        for user in users_qs:
            try:
                notify(user, notif_type, title, body, channels=channels)
                count += 1
            except Exception:
                pass
        return Response({'detail': f'Notification envoyée à {count} utilisateurs.'})
