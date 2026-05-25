from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsAdmin, IsActiveVendor
from core.pagination import StandardPagination
from .models import SavRequest, SavMessage
from .serializers import (
    SavRequestSerializer, SavRequestResolveSerializer,
    SavRequestAdminSerializer, SavMessageSerializer,
)


@extend_schema(tags=['sav'])
class MySavRequestListCreateView(generics.ListCreateAPIView):
    """Mes demandes SAV — liste et création."""
    serializer_class = SavRequestSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = SavRequest.objects.filter(user=self.request.user).select_related(
            'order', 'order_item'
        ).prefetch_related('images')
        type_filter = self.request.query_params.get('type')
        status_filter = self.request.query_params.get('status')
        if type_filter:
            qs = qs.filter(type=type_filter)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        # Vérifier que l'order_item appartient bien à l'utilisateur
        order_item = serializer.validated_data['order_item']
        if order_item.order.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Cet article ne vous appartient pas.")
        serializer.save(user=self.request.user)


@extend_schema(tags=['sav'])
class MySavRequestDetailView(generics.RetrieveAPIView):
    """Détail d'une demande SAV du client."""
    serializer_class = SavRequestAdminSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SavRequest.objects.filter(user=self.request.user).prefetch_related(
            'images', 'messages__attachments', 'messages__sender'
        )


@extend_schema(tags=['sav'])
class MySavRequestCancelView(APIView):
    """Annuler une demande SAV en attente."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        sav = generics.get_object_or_404(SavRequest, pk=pk, user=request.user)
        if sav.status not in ('pending',):
            return Response(
                {'detail': 'Seules les demandes en attente peuvent être annulées.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        sav.status = 'cancelled'
        sav.save(update_fields=['status', 'updated_at'])
        return Response({'detail': 'Demande annulée.'})


@extend_schema(tags=['sav'])
class SavMessageCreateView(generics.CreateAPIView):
    """Ajouter un message à une demande SAV."""
    serializer_class = SavMessageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_create(self, serializer):
        sav = generics.get_object_or_404(SavRequest, pk=self.kwargs['pk'])
        # Client ou admin peuvent écrire — les vendeurs n'ont plus accès
        if sav.user != self.request.user and self.request.user.role != 'admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()
        # Seul le staff peut envoyer des notes internes
        is_internal = serializer.validated_data.get('is_internal', False)
        if is_internal and self.request.user.role not in ('admin',):
            serializer.validated_data['is_internal'] = False
        serializer.save(request=sav, sender=self.request.user)


# ── Admin ────────────────────────────────────────────────────────────────────

@extend_schema(tags=['sav'])
class AdminSavListView(generics.ListAPIView):
    """Admin — liste toutes les demandes SAV avec filtres."""
    serializer_class = SavRequestAdminSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = SavRequest.objects.select_related(
            'user', 'order', 'order_item'
        ).prefetch_related('images', 'messages')
        for param in ('type', 'status', 'reason'):
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{param: val})
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(reference__icontains=search) | qs.filter(
                user__email__icontains=search
            )
        return qs.order_by('-created_at')


@extend_schema(tags=['sav'])
class AdminSavDetailView(generics.RetrieveUpdateAPIView):
    """Admin — détail et mise à jour d'une demande SAV."""
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = SavRequest.objects.prefetch_related('images', 'messages__attachments', 'messages__sender')

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return SavRequestResolveSerializer
        return SavRequestAdminSerializer


@extend_schema(tags=['sav'])
class AdminSavResolveView(APIView):
    """Admin — résoudre une demande SAV (approve/reject/complete)."""
    permission_classes = [IsAuthenticated, IsAdmin]

    STATUS_LABELS = {
        'approved':   'Approuvé',
        'rejected':   'Rejeté',
        'processing': 'En traitement',
        'completed':  'Terminé',
    }

    def post(self, request, pk):
        sav = generics.get_object_or_404(SavRequest, pk=pk)
        new_status = request.data.get('status')
        allowed = ('approved', 'rejected', 'processing', 'completed')
        if new_status not in allowed:
            return Response(
                {'detail': f'Statut invalide. Valeurs autorisées: {allowed}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notes = request.data.get('resolution_notes', '').strip()
        sav.status = new_status
        sav.resolution_notes = notes or sav.resolution_notes
        sav.resolved_by = request.user
        sav.resolved_at = timezone.now()

        if new_status == 'completed' and request.data.get('refund_amount'):
            sav.refund_amount = request.data.get('refund_amount')
            sav.refund_method = request.data.get('refund_method', 'wallet')
            sav.refunded_at = timezone.now()

        sav.save()

        # Créer un message de décision visible par le client
        label = self.STATUS_LABELS.get(new_status, new_status)
        body = f"[DECISION:{new_status}] {label}"
        if notes:
            body += f"\n{notes}"
        SavMessage.objects.create(
            request=sav,
            sender=request.user,
            content=body,
            is_internal=False,
        )

        # Recharger avec messages à jour
        sav.refresh_from_db()
        serializer = SavRequestAdminSerializer(
            sav,
            context={'request': request},
        )
        return Response(serializer.data)


@extend_schema(tags=['sav'])
class VendorSavListView(generics.ListAPIView):
    """Vendeur — demandes SAV concernant sa boutique."""
    serializer_class = SavRequestSerializer
    permission_classes = [IsAuthenticated, IsActiveVendor]
    pagination_class = StandardPagination

    def get_queryset(self):
        store = self.request.user.store
        qs = SavRequest.objects.filter(
            order_item__store=store
        ).select_related('user', 'order', 'order_item').prefetch_related('images')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by('-created_at')
