from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import LiveSession, LiveProduct, LiveComment, LiveOrder
from .serializers import (
    LiveSessionListSerializer,
    LiveSessionDetailSerializer,
    LiveSessionCreateSerializer,
    LiveSessionUpdateSerializer,
    LiveProductSerializer,
    LiveProductWriteSerializer,
    LiveCommentSerializer,
)


class IsVendor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, 'store')


class IsSessionHost(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        session = obj if isinstance(obj, LiveSession) else obj.session
        return session.host == request.user or request.user.is_staff


# ── Public ────────────────────────────────────────────────────────────────────

class LiveSessionPublicListView(generics.ListAPIView):
    serializer_class = LiveSessionListSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(tags=['Live Shopping'], summary='Sessions live en cours et programmées')
    def get_queryset(self):
        return LiveSession.objects.filter(
            status__in=['scheduled', 'live']
        ).select_related('store', 'host').order_by('-status', 'scheduled_at')


class LiveSessionPublicDetailView(generics.RetrieveAPIView):
    serializer_class = LiveSessionDetailSerializer
    permission_classes = [permissions.AllowAny]
    queryset = LiveSession.objects.select_related('store', 'host')
    lookup_field = 'pk'

    @extend_schema(tags=['Live Shopping'], summary='Détail d\'une session live')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class LiveSessionByRoomView(generics.RetrieveAPIView):
    serializer_class = LiveSessionDetailSerializer
    permission_classes = [permissions.AllowAny]
    queryset = LiveSession.objects.select_related('store', 'host')
    lookup_field = 'room_id'

    @extend_schema(tags=['Live Shopping'], summary='Rejoindre une session live par room_id')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# ── Vendor ────────────────────────────────────────────────────────────────────

class VendorLiveSessionListView(generics.ListCreateAPIView):
    permission_classes = [IsVendor]

    @extend_schema(tags=['Live Shopping'], summary='Mes sessions live (vendeur)')
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LiveSessionCreateSerializer
        return LiveSessionListSerializer

    def get_queryset(self):
        return LiveSession.objects.filter(store=self.request.user.store).order_by('-created_at')


class VendorLiveSessionDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsVendor, IsSessionHost]
    lookup_field = 'pk'

    @extend_schema(tags=['Live Shopping'], summary='Détail / modification d\'une session live (vendeur)')
    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return LiveSessionUpdateSerializer
        return LiveSessionDetailSerializer

    def get_queryset(self):
        return LiveSession.objects.filter(store=self.request.user.store)


class VendorLiveStartView(APIView):
    permission_classes = [IsVendor]

    @extend_schema(tags=['Live Shopping'], summary='Démarrer une session live')
    def post(self, request, pk):
        session = _get_vendor_session(request, pk)
        if not session:
            return Response({'detail': 'Session introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if session.status != 'scheduled':
            return Response({'detail': 'Seules les sessions programmées peuvent être démarrées.'}, status=status.HTTP_400_BAD_REQUEST)
        session.status = 'live'
        session.started_at = timezone.now()
        session.save(update_fields=['status', 'started_at'])
        _broadcast_status(session, 'session_started')
        return Response(LiveSessionDetailSerializer(session, context={'request': request}).data)


class VendorLiveEndView(APIView):
    permission_classes = [IsVendor]

    @extend_schema(tags=['Live Shopping'], summary='Terminer une session live')
    def post(self, request, pk):
        session = _get_vendor_session(request, pk)
        if not session:
            return Response({'detail': 'Session introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if session.status != 'live':
            return Response({'detail': 'La session n\'est pas en direct.'}, status=status.HTTP_400_BAD_REQUEST)
        session.status = 'ended'
        session.ended_at = timezone.now()
        session.save(update_fields=['status', 'ended_at'])
        _broadcast_status(session, 'session_ended')
        return Response(LiveSessionDetailSerializer(session, context={'request': request}).data)


class VendorLiveProductListView(generics.ListCreateAPIView):
    permission_classes = [IsVendor]

    @extend_schema(tags=['Live Shopping'], summary='Produits d\'une session live (vendeur)')
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return LiveProductWriteSerializer
        return LiveProductSerializer

    def get_queryset(self):
        return LiveProduct.objects.filter(
            session__store=self.request.user.store,
            session__pk=self.kwargs['session_pk']
        ).select_related('product', 'variant')

    def perform_create(self, serializer):
        session = LiveSession.objects.get(pk=self.kwargs['session_pk'], store=self.request.user.store)
        serializer.save(session=session)


class VendorLiveProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsVendor]

    @extend_schema(tags=['Live Shopping'], summary='Produit live — modifier / supprimer')
    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return LiveProductWriteSerializer
        return LiveProductSerializer

    def get_queryset(self):
        return LiveProduct.objects.filter(session__store=self.request.user.store)


class VendorFeatureProductView(APIView):
    permission_classes = [IsVendor]

    @extend_schema(tags=['Live Shopping'], summary='Mettre un produit en avant pendant le live')
    def post(self, request, session_pk, pk):
        try:
            lp = LiveProduct.objects.get(pk=pk, session__pk=session_pk, session__store=request.user.store)
        except LiveProduct.DoesNotExist:
            return Response({'detail': 'Produit introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        lp.is_featured = True
        lp.save()
        _broadcast_feature_product(lp)
        return Response(LiveProductSerializer(lp, context={'request': request}).data)


# ── Comments ──────────────────────────────────────────────────────────────────

class LiveCommentListView(generics.ListAPIView):
    serializer_class = LiveCommentSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(tags=['Live Shopping'], summary='Commentaires d\'une session live')
    def get_queryset(self):
        return LiveComment.objects.filter(
            session__pk=self.kwargs['session_pk'],
            is_deleted=False,
        ).select_related('user').order_by('-created_at')[:200]


# ── Admin ─────────────────────────────────────────────────────────────────────

class AdminLiveSessionListView(generics.ListAPIView):
    serializer_class = LiveSessionListSerializer
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        tags=['Live Shopping'],
        summary='Toutes les sessions live (admin)',
        parameters=[
            OpenApiParameter('status', OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('store_id', OpenApiTypes.INT, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get_queryset(self):
        qs = LiveSession.objects.select_related('store', 'host').order_by('-created_at')
        if self.request.query_params.get('status'):
            qs = qs.filter(status=self.request.query_params['status'])
        if self.request.query_params.get('store_id'):
            qs = qs.filter(store_id=self.request.query_params['store_id'])
        return qs


class AdminLiveSessionDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = LiveSessionDetailSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = LiveSession.objects.select_related('store', 'host')

    @extend_schema(tags=['Live Shopping'], summary='Détail session live (admin)')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_vendor_session(request, pk):
    try:
        return LiveSession.objects.get(pk=pk, store=request.user.store)
    except LiveSession.DoesNotExist:
        return None


def _broadcast_status(session, event_type):
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'live_{session.room_id}',
            {'type': 'session_status_event', 'status': event_type}
        )


def _broadcast_feature_product(live_product):
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'live_{live_product.session.room_id}',
            {'type': 'product_featured_event', 'live_product': {'id': live_product.pk, 'product_name': live_product.product.name}}
        )
