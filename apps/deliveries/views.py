from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsDelivery, IsAdmin
from core.pagination import StandardPagination
from .models import DeliveryZone, RelayPoint, Delivery, DeliveryHistory, DeliveryProfile
from .serializers import (
    DeliveryZoneSerializer, RelayPointSerializer, DeliverySerializer,
    DeliveryTrackingSerializer, DeliveryHistorySerializer,
    DeliveryPersonSerializer, DeliveryPersonWriteSerializer,
)


@extend_schema(tags=['deliveries'])
class DeliveryZoneListView(generics.ListAPIView):
    serializer_class = DeliveryZoneSerializer
    permission_classes = [AllowAny]
    queryset = DeliveryZone.objects.filter(is_active=True)


@extend_schema(tags=['deliveries'])
class DeliveryZoneCalculateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        city = request.data.get('city', '').strip().lower()
        weight = float(request.data.get('weight', 0))
        zone = None
        for z in DeliveryZone.objects.filter(is_active=True):
            if any(c.lower() == city for c in z.cities):
                zone = z
                break
        if not zone:
            return Response({'detail': 'Aucune zone de livraison disponible pour cette ville.'}, status=status.HTTP_404_NOT_FOUND)
        cost = float(zone.base_price) + (float(zone.price_per_kg) * weight)
        return Response({
            'zone': DeliveryZoneSerializer(zone).data,
            'cost': cost,
            'estimated_days': zone.estimated_days,
        })


@extend_schema(tags=['deliveries'])
class RelayPointListView(generics.ListAPIView):
    serializer_class = RelayPointSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = RelayPoint.objects.filter(is_active=True)
        city = self.request.query_params.get('city')
        if city:
            qs = qs.filter(city__icontains=city)
        return qs


@extend_schema(tags=['deliveries'])
class RelayPointDetailView(generics.RetrieveAPIView):
    serializer_class = RelayPointSerializer
    permission_classes = [AllowAny]
    queryset = RelayPoint.objects.filter(is_active=True)


@extend_schema(tags=['deliveries'])
class TrackingView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, tracking_number):
        try:
            delivery = Delivery.objects.get(tracking_number=tracking_number)
        except Delivery.DoesNotExist:
            return Response({'detail': 'Numéro de suivi introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = DeliveryTrackingSerializer(delivery)
        return Response(serializer.data)


@extend_schema(tags=['deliveries'])
class DeliveryPersonListView(generics.ListAPIView):
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated, IsDelivery]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Delivery.objects.filter(delivery_person=self.request.user).select_related('order', 'relay_point')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by('-created_at')


@extend_schema(tags=['deliveries'])
class DeliveryUpdateStatusView(APIView):
    permission_classes = [IsAuthenticated, IsDelivery]

    def patch(self, request, pk):
        try:
            delivery = Delivery.objects.get(pk=pk, delivery_person=request.user)
        except Delivery.DoesNotExist:
            return Response({'detail': 'Livraison introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        new_status = request.data.get('status')
        if new_status not in dict(Delivery.STATUS_CHOICES):
            return Response({'detail': 'Statut invalide.'}, status=status.HTTP_400_BAD_REQUEST)
        delivery.status = new_status
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        if lat:
            delivery.current_latitude = lat
        if lng:
            delivery.current_longitude = lng
        if new_status == 'delivered':
            delivery.actual_delivery_date = timezone.now()
            delivery.order.status = 'delivered'
            delivery.order.save(update_fields=['status'])
        delivery.save()
        DeliveryHistory.objects.create(
            delivery=delivery,
            status=new_status,
            location=request.data.get('location', ''),
            note=request.data.get('note', ''),
        )
        return Response(DeliverySerializer(delivery).data)


@extend_schema(tags=['deliveries'])
class DeliverySignatureView(APIView):
    permission_classes = [IsAuthenticated, IsDelivery]

    def post(self, request, pk):
        try:
            delivery = Delivery.objects.get(pk=pk, delivery_person=request.user)
        except Delivery.DoesNotExist:
            return Response({'detail': 'Livraison introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        signature = request.FILES.get('signature')
        if not signature:
            return Response({'detail': 'Signature requise.'}, status=status.HTTP_400_BAD_REQUEST)
        delivery.signature_image = signature
        delivery.status = 'delivered'
        delivery.actual_delivery_date = timezone.now()
        delivery.save(update_fields=['signature_image', 'status', 'actual_delivery_date'])
        delivery.order.status = 'delivered'
        delivery.order.save(update_fields=['status'])
        DeliveryHistory.objects.create(delivery=delivery, status='delivered', note='Signature recueillie.')
        return Response(DeliverySerializer(delivery).data)


@extend_schema(tags=['deliveries'])
class AdminDeliveryListView(generics.ListAPIView):
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Delivery.objects.all().select_related('order', 'delivery_person', 'relay_point')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(tracking_number__icontains=search) |
                Q(order__order_number__icontains=search) |
                Q(order__user__email__icontains=search) |
                Q(order__user__first_name__icontains=search)
            )
        return qs.order_by('-created_at')


@extend_schema(tags=['deliveries'])
class AdminAssignDeliveryView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        try:
            delivery = Delivery.objects.get(pk=pk)
        except Delivery.DoesNotExist:
            return Response({'detail': 'Livraison introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        person_id = request.data.get('delivery_person_id')
        try:
            person = User.objects.get(pk=person_id, role='delivery')
        except User.DoesNotExist:
            return Response({'detail': 'Livreur introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        delivery.delivery_person = person
        delivery.status = 'assigned'
        delivery.save(update_fields=['delivery_person', 'status'])
        DeliveryHistory.objects.create(delivery=delivery, status='assigned', note=f'Assigné à {person.full_name}')
        return Response(DeliverySerializer(delivery).data)


# ── Dashboard livreur ─────────────────────────────────────────────────────────

@extend_schema(tags=['deliveries'])
class DeliveryPersonDashboardView(APIView):
    """Tableau de bord complet du livreur connecté."""
    permission_classes = [IsAuthenticated, IsDelivery]

    def get(self, request):
        from django.db.models import Count, Q
        from django.utils import timezone
        from datetime import timedelta

        user = request.user
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())

        qs = Delivery.objects.filter(delivery_person=user)

        # Stats globales
        stats = qs.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            assigned=Count('id', filter=Q(status='assigned')),
            picked_up=Count('id', filter=Q(status='picked_up')),
            in_transit=Count('id', filter=Q(status='in_transit')),
            delivered=Count('id', filter=Q(status='delivered')),
            failed=Count('id', filter=Q(status='failed')),
        )

        # Aujourd'hui : livraisons avec une activité aujourd'hui (updated_at)
        # Couvre les cas : assignée, récupérée, en transit ou livrée aujourd'hui
        delivered_today = qs.filter(
            Q(status='delivered') &
            (Q(actual_delivery_date__date=today) | Q(updated_at__date=today))
        ).count()
        active_today = qs.filter(updated_at__date=today).count()

        # Cette semaine : même logique sur 7 jours glissants
        delivered_this_week = qs.filter(
            Q(status='delivered') &
            (Q(actual_delivery_date__date__gte=week_start) | Q(updated_at__date__gte=week_start))
        ).count()
        active_this_week = qs.filter(updated_at__date__gte=week_start).count()

        # Livraisons actives (à faire maintenant)
        active = qs.filter(status__in=['assigned', 'picked_up', 'in_transit']).select_related('order', 'relay_point').order_by('estimated_delivery_date')
        active_data = DeliverySerializer(active, many=True, context={'request': request}).data

        return Response({
            'stats': {
                **stats,
                'delivered_today': delivered_today,
                'active_today': active_today,
                'delivered_this_week': delivered_this_week,
                'active_this_week': active_this_week,
            },
            'active_deliveries': active_data,
        })


@extend_schema(tags=['deliveries'])
class DeliveryPersonDetailView(generics.RetrieveAPIView):
    """Détail d'une livraison assignée au livreur."""
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated, IsDelivery]

    def get_object(self):
        try:
            return Delivery.objects.get(pk=self.kwargs['pk'], delivery_person=self.request.user)
        except Delivery.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('Livraison introuvable.')


@extend_schema(tags=['deliveries'])
class DeliveryPersonPickupView(APIView):
    """Le livreur confirme la récupération du colis chez le vendeur."""
    permission_classes = [IsAuthenticated, IsDelivery]

    def post(self, request, pk):
        try:
            delivery = Delivery.objects.get(pk=pk, delivery_person=request.user)
        except Delivery.DoesNotExist:
            return Response({'detail': 'Livraison introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if delivery.status != 'assigned':
            return Response({'detail': 'Statut actuel incompatible.'}, status=status.HTTP_400_BAD_REQUEST)
        delivery.status = 'picked_up'
        delivery.save(update_fields=['status'])
        DeliveryHistory.objects.create(
            delivery=delivery, status='picked_up',
            location=request.data.get('location', ''),
            note='Colis récupéré chez le vendeur.',
        )
        return Response(DeliverySerializer(delivery, context={'request': request}).data)


@extend_schema(tags=['deliveries'])
class DeliveryPersonUpdateGPSView(APIView):
    """Met à jour la position GPS du livreur et diffuse via WebSocket."""
    permission_classes = [IsAuthenticated, IsDelivery]

    def patch(self, request, pk):
        try:
            delivery = Delivery.objects.get(pk=pk, delivery_person=request.user)
        except Delivery.DoesNotExist:
            return Response({'detail': 'Livraison introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        if lat is None or lng is None:
            return Response({'detail': 'latitude et longitude requis.'}, status=status.HTTP_400_BAD_REQUEST)

        delivery.current_latitude = lat
        delivery.current_longitude = lng
        delivery.save(update_fields=['current_latitude', 'current_longitude'])

        # Broadcast via WebSocket
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'delivery_{delivery.tracking_number}',
                {
                    'type': 'gps_update',
                    'latitude': str(lat),
                    'longitude': str(lng),
                    'tracking_number': delivery.tracking_number,
                }
            )

        return Response({'latitude': lat, 'longitude': lng})


@extend_schema(tags=['deliveries'])
class DeliveryPersonHistoryView(generics.ListAPIView):
    """Historique des livraisons terminées du livreur."""
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated, IsDelivery]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Delivery.objects.filter(
            delivery_person=self.request.user,
            status__in=['delivered', 'failed'],
        ).select_related('order').order_by('-actual_delivery_date')


@extend_schema(tags=['deliveries'])
class AdminDeliveryPersonListView(APIView):
    """Admin — liste et création de livreurs."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def _annotated_qs(self):
        from django.contrib.auth import get_user_model
        from django.db.models import Count, Q
        User = get_user_model()
        return User.objects.filter(role='delivery').select_related('delivery_profile').prefetch_related(
            'delivery_profile__coverage_zones'
        ).annotate(
            active_count=Count('deliveries', filter=Q(deliveries__status__in=['assigned', 'picked_up', 'in_transit'])),
            total_delivered=Count('deliveries', filter=Q(deliveries__status='delivered')),
        ).order_by('first_name', 'last_name')

    def get(self, request):
        qs = self._annotated_qs()
        # Rename annotated fields to match serializer
        for u in qs:
            u.active_deliveries = u.active_count
            u.total_delivered_count = u.total_delivered
        data = DeliveryPersonSerializer(qs, many=True).data
        return Response(data)

    def post(self, request):
        serializer = DeliveryPersonWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # Reload with annotations for response
        from django.contrib.auth import get_user_model
        from django.db.models import Count, Q
        User = get_user_model()
        u = User.objects.select_related('delivery_profile').prefetch_related(
            'delivery_profile__coverage_zones'
        ).annotate(
            active_count=Count('deliveries', filter=Q(deliveries__status__in=['assigned', 'picked_up', 'in_transit'])),
            total_delivered=Count('deliveries', filter=Q(deliveries__status='delivered')),
        ).get(pk=user.pk)
        u.active_deliveries = u.active_count
        u.total_delivered_count = u.total_delivered
        return Response(DeliveryPersonSerializer(u).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['deliveries'])
class AdminDeliveryPersonDetailView(APIView):
    """Admin — détail, modification, suppression d'un livreur."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def _get_user(self, pk):
        from django.contrib.auth import get_user_model
        from django.db.models import Count, Q
        User = get_user_model()
        try:
            return User.objects.select_related('delivery_profile').prefetch_related(
                'delivery_profile__coverage_zones'
            ).annotate(
                active_count=Count('deliveries', filter=Q(deliveries__status__in=['assigned', 'picked_up', 'in_transit'])),
                total_delivered=Count('deliveries', filter=Q(deliveries__status='delivered')),
            ).get(pk=pk, role='delivery')
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        u = self._get_user(pk)
        if not u:
            return Response({'detail': 'Livreur introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        u.active_deliveries = u.active_count
        return Response(DeliveryPersonSerializer(u).data)

    def patch(self, request, pk):
        u = self._get_user(pk)
        if not u:
            return Response({'detail': 'Livreur introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = DeliveryPersonWriteSerializer(u, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        u = self._get_user(user.pk)
        u.active_deliveries = u.active_count
        return Response(DeliveryPersonSerializer(u).data)

    def delete(self, request, pk):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            u = User.objects.get(pk=pk, role='delivery')
        except User.DoesNotExist:
            return Response({'detail': 'Livreur introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        u.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['deliveries'])
class AdminDeliveryDetailView(generics.RetrieveUpdateAPIView):
    """Admin — détail d'une livraison."""
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Delivery.objects.select_related('order', 'delivery_person', 'relay_point').prefetch_related('history')


@extend_schema(tags=['deliveries'])
class AdminReassignDeliveryView(APIView):
    """Admin — réassigner une livraison à un autre livreur."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        try:
            delivery = Delivery.objects.get(pk=pk)
        except Delivery.DoesNotExist:
            return Response({'detail': 'Livraison introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        person_id = request.data.get('delivery_person_id')
        try:
            person = User.objects.get(pk=person_id, role='delivery')
        except User.DoesNotExist:
            return Response({'detail': 'Livreur introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        old_name = delivery.delivery_person.get_full_name() if delivery.delivery_person else '—'
        delivery.delivery_person = person
        delivery.status = 'assigned'
        delivery.save(update_fields=['delivery_person', 'status'])
        DeliveryHistory.objects.create(
            delivery=delivery, status='assigned',
            note=f'Réassigné de {old_name} à {person.get_full_name() or person.email}',
        )
        return Response(DeliverySerializer(delivery).data)


@extend_schema(tags=['deliveries'])
class AdminRelayPointListCreateView(generics.ListCreateAPIView):
    """Admin — liste et création de points relais."""
    serializer_class = RelayPointSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        qs = RelayPoint.objects.all()
        city = self.request.query_params.get('city')
        if city:
            qs = qs.filter(city__icontains=city)
        active = self.request.query_params.get('is_active')
        if active is not None:
            qs = qs.filter(is_active=active.lower() == 'true')
        return qs.order_by('city', 'name')


@extend_schema(tags=['deliveries'])
class AdminRelayPointDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin — détail, modification, suppression d'un point relais."""
    serializer_class = RelayPointSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = RelayPoint.objects.all()


@extend_schema(tags=['deliveries'])
class AdminDeliveryZoneListCreateView(generics.ListCreateAPIView):
    """Admin — liste et création de zones de livraison."""
    serializer_class = DeliveryZoneSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = DeliveryZone.objects.all().order_by('name')


@extend_schema(tags=['deliveries'])
class AdminDeliveryZoneDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin — détail, modification, suppression d'une zone de livraison."""
    serializer_class = DeliveryZoneSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = DeliveryZone.objects.all()


@extend_schema(tags=['deliveries'])
class ClientDeliveryByOrderView(APIView):
    """Client — récupérer la livraison d'une commande."""
    permission_classes = [IsAuthenticated]

    def get(self, request, order_number):
        try:
            delivery = Delivery.objects.select_related('relay_point').prefetch_related('history').get(
                order__order_number=order_number,
                order__user=request.user,
            )
        except Delivery.DoesNotExist:
            return Response({'detail': 'Livraison introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(DeliveryTrackingSerializer(delivery).data)


@extend_schema(tags=['deliveries'])
class ClientUpdateDeliveryAddressView(APIView):
    """Client — modifier l'adresse ou le point relais d'une livraison encore en attente."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, order_number):
        try:
            delivery = Delivery.objects.get(
                order__order_number=order_number,
                order__user=request.user,
            )
        except Delivery.DoesNotExist:
            return Response({'detail': 'Livraison introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        if delivery.status not in ('pending',):
            return Response({'detail': 'Impossible de modifier une livraison déjà en cours.'}, status=status.HTTP_400_BAD_REQUEST)

        delivery_type = request.data.get('type', delivery.type)
        delivery.type = delivery_type

        if delivery_type == 'relay_point':
            relay_id = request.data.get('relay_point')
            if relay_id:
                try:
                    delivery.relay_point = RelayPoint.objects.get(pk=relay_id, is_active=True)
                except RelayPoint.DoesNotExist:
                    return Response({'detail': 'Point relais introuvable.'}, status=status.HTTP_404_NOT_FOUND)
            delivery.delivery_address = None
        else:
            delivery.delivery_address = request.data.get('delivery_address', delivery.delivery_address)
            delivery.relay_point = None

        delivery.save()
        return Response(DeliveryTrackingSerializer(delivery).data)


@extend_schema(tags=['deliveries'])
class QRValidateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        qr_data = request.data.get('qr_code')
        if not qr_data:
            return Response({'detail': 'QR code requis.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            delivery = Delivery.objects.get(qr_code=qr_data, type='relay_point')
        except Delivery.DoesNotExist:
            return Response({'detail': 'QR code invalide.'}, status=status.HTTP_404_NOT_FOUND)
        if delivery.status == 'delivered':
            return Response({'detail': 'Colis déjà retiré.'}, status=status.HTTP_400_BAD_REQUEST)
        delivery.status = 'delivered'
        delivery.actual_delivery_date = timezone.now()
        delivery.save(update_fields=['status', 'actual_delivery_date'])
        delivery.order.status = 'delivered'
        delivery.order.save(update_fields=['status'])
        DeliveryHistory.objects.create(delivery=delivery, status='delivered', note='Retrait validé par QR code.')
        return Response({'detail': 'Retrait validé.', 'tracking_number': delivery.tracking_number})
