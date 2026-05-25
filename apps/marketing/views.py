from django.utils import timezone
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Campaign, AbandonedCartReminder, Unsubscribe
from .serializers import (
    CampaignSerializer,
    CampaignSendSerializer,
    AbandonedCartReminderSerializer,
    UnsubscribeSerializer,
)


# ── Admin — Campagnes ─────────────────────────────────────────────────────────

class AdminCampaignListView(generics.ListCreateAPIView):
    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        tags=['Marketing'],
        summary='Campagnes marketing (liste / création)',
        parameters=[
            OpenApiParameter('channel', OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter('status', OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get_queryset(self):
        qs = Campaign.objects.select_related('created_by').order_by('-created_at')
        if self.request.query_params.get('channel'):
            qs = qs.filter(channel=self.request.query_params['channel'])
        if self.request.query_params.get('status'):
            qs = qs.filter(status=self.request.query_params['status'])
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AdminCampaignDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CampaignSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Campaign.objects.all()

    @extend_schema(tags=['Marketing'], summary='Détail / modification / suppression d\'une campagne')
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def perform_destroy(self, instance):
        if instance.status == 'sending':
            from rest_framework.exceptions import ValidationError
            raise ValidationError('Impossible de supprimer une campagne en cours d\'envoi.')
        instance.delete()


class AdminCampaignSendView(APIView):
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        tags=['Marketing'],
        summary='Envoyer ou programmer une campagne',
        request=CampaignSendSerializer,
    )
    def post(self, request, pk):
        try:
            campaign = Campaign.objects.get(pk=pk)
        except Campaign.DoesNotExist:
            return Response({'detail': 'Campagne introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        if campaign.status not in ('draft', 'scheduled'):
            return Response({'detail': f'Impossible d\'envoyer une campagne au statut {campaign.status}.'},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = CampaignSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        if d.get('send_now'):
            from .tasks import send_campaign_task
            send_campaign_task.delay(campaign.pk)
            return Response({'detail': 'Envoi déclenché en arrière-plan.', 'campaign_id': campaign.pk})
        else:
            campaign.scheduled_at = d['scheduled_at']
            campaign.status = 'scheduled'
            campaign.save(update_fields=['scheduled_at', 'status'])
            return Response(CampaignSerializer(campaign).data)


class AdminCampaignDuplicateView(APIView):
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(tags=['Marketing'], summary='Dupliquer une campagne')
    def post(self, request, pk):
        try:
            original = Campaign.objects.get(pk=pk)
        except Campaign.DoesNotExist:
            return Response({'detail': 'Campagne introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        copy = Campaign.objects.create(
            name=f'Copie — {original.name}',
            channel=original.channel,
            audience=original.audience,
            subject=original.subject,
            content=original.content,
            cta_url=original.cta_url,
            cta_label=original.cta_label,
            created_by=request.user,
            status='draft',
        )
        return Response(CampaignSerializer(copy).data, status=status.HTTP_201_CREATED)


# ── Admin — Paniers abandonnés ────────────────────────────────────────────────

class AdminAbandonedCartListView(generics.ListAPIView):
    serializer_class = AbandonedCartReminderSerializer
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        tags=['Marketing'],
        summary='Paniers abandonnés',
        parameters=[
            OpenApiParameter('status', OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False),
        ],
    )
    def get_queryset(self):
        qs = AbandonedCartReminder.objects.select_related('user', 'cart').order_by('-created_at')
        if self.request.query_params.get('status'):
            qs = qs.filter(status=self.request.query_params['status'])
        return qs


class AdminTriggerAbandonedCartCheck(APIView):
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(tags=['Marketing'], summary='Déclencher manuellement la vérification des paniers abandonnés')
    def post(self, request):
        from .tasks import check_abandoned_carts_task
        check_abandoned_carts_task.delay()
        return Response({'detail': 'Vérification des paniers abandonnés déclenchée.'})


# ── Utilisateur — Désabonnement ───────────────────────────────────────────────

class UnsubscribeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Marketing'], summary='Se désabonner d\'un canal marketing')
    def post(self, request):
        serializer = UnsubscribeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': f'Désabonné du canal {serializer.validated_data["channel"]}.'})

    @extend_schema(tags=['Marketing'], summary='Mes désabonnements')
    def get(self, request):
        items = Unsubscribe.objects.filter(user=request.user)
        return Response(UnsubscribeSerializer(items, many=True).data)


class ResubscribeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(tags=['Marketing'], summary='Se réabonner à un canal')
    def delete(self, request, channel):
        Unsubscribe.objects.filter(user=request.user, channel=channel).delete()
        return Response({'detail': f'Réabonné au canal {channel}.'})
