from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsAdmin, IsAdminOrReadOnly
from core.pagination import StandardPagination
from .models import (
    FAQ, FAQCategory, SupportTicket, TicketMessage,
    Dispute, DisputeEvidence, DisputeMessage,
)
from .serializers import (
    FAQSerializer, FAQCategorySerializer,
    SupportTicketSerializer, SupportTicketDetailSerializer, TicketMessageSerializer,
    DisputeSerializer, DisputeDetailSerializer, DisputeEvidenceSerializer,
    DisputeMessageSerializer, DisputeDecisionSerializer,
)


# ── FAQ ──────────────────────────────────────────────────────────────────────

@extend_schema(tags=['support'])
class FAQCategoryListView(generics.ListAPIView):
    serializer_class = FAQCategorySerializer
    permission_classes = [AllowAny]
    queryset = FAQCategory.objects.filter(is_active=True).prefetch_related('faqs')


@extend_schema(tags=['support'])
class FAQListView(generics.ListAPIView):
    serializer_class = FAQSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = FAQ.objects.filter(is_published=True)
        category = self.request.query_params.get('category')
        audience = self.request.query_params.get('audience')
        search = self.request.query_params.get('search')
        if category:
            qs = qs.filter(faq_category__slug=category)
        if audience:
            qs = qs.filter(audience__in=(audience, 'all'))
        if search:
            qs = qs.filter(question__icontains=search) | qs.filter(answer__icontains=search)
        return qs.order_by('order', 'question')


@extend_schema(tags=['support'])
class FAQDetailView(generics.RetrieveAPIView):
    serializer_class = FAQSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return FAQ.objects.filter(is_published=True)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        FAQ.objects.filter(pk=instance.pk).update(views=instance.views + 1)
        return Response(self.get_serializer(instance).data)


@extend_schema(tags=['support'])
class AdminFAQListCreateView(generics.ListCreateAPIView):
    serializer_class = FAQSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = FAQ.objects.all().select_related('faq_category')


@extend_schema(tags=['support'])
class AdminFAQDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FAQSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = FAQ.objects.all()


# ── Tickets support ───────────────────────────────────────────────────────────

@extend_schema(tags=['support'])
class MySupportTicketListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        return SupportTicketSerializer

    def get_queryset(self):
        qs = SupportTicket.objects.filter(user=self.request.user)
        st = self.request.query_params.get('status')
        if st:
            qs = qs.filter(status=st)
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        ticket = serializer.save(user=self.request.user)
        message = self.request.data.get('message', '').strip()
        if message:
            TicketMessage.objects.create(ticket=ticket, sender=self.request.user, content=message)


@extend_schema(tags=['support'])
class MySupportTicketDetailView(generics.RetrieveAPIView):
    serializer_class = SupportTicketDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user).prefetch_related(
            'messages__attachments'
        )


@extend_schema(tags=['support'])
class TicketMessageCreateView(generics.CreateAPIView):
    serializer_class = TicketMessageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_create(self, serializer):
        ticket = generics.get_object_or_404(SupportTicket, pk=self.kwargs['pk'])
        if ticket.user != self.request.user and self.request.user.role != 'admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()
        if ticket.status in ('resolved', 'closed'):
            from rest_framework.exceptions import ValidationError
            raise ValidationError('Ce ticket est clôturé.')
        # Réouvrir si en attente client
        if ticket.status == 'waiting_customer' and ticket.user == self.request.user:
            ticket.status = 'open'
            ticket.save(update_fields=['status'])
        is_internal = serializer.validated_data.get('is_internal', False)
        if is_internal and self.request.user.role != 'admin':
            serializer.validated_data['is_internal'] = False
        serializer.save(ticket=ticket, sender=self.request.user)


@extend_schema(tags=['support'])
class TicketRateView(APIView):
    """Client évalue la satisfaction après résolution."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        ticket = generics.get_object_or_404(SupportTicket, pk=pk, user=request.user)
        score = request.data.get('score')
        if not score or int(score) not in range(1, 6):
            return Response({'detail': 'Score invalide (1-5).'}, status=status.HTTP_400_BAD_REQUEST)
        ticket.satisfaction_score = int(score)
        ticket.save(update_fields=['satisfaction_score'])
        return Response({'detail': 'Merci pour votre évaluation.'})


# ── Admin tickets ─────────────────────────────────────────────────────────────

@extend_schema(tags=['support'])
class AdminTicketListView(generics.ListAPIView):
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = SupportTicket.objects.select_related('user', 'assigned_to')
        for param in ('status', 'category', 'priority'):
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{param: val})
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(reference__icontains=search) | qs.filter(subject__icontains=search)
        return qs.order_by('-created_at')


@extend_schema(tags=['support'])
class AdminTicketDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = SupportTicketDetailSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = SupportTicket.objects.prefetch_related('messages__attachments')

    def perform_update(self, serializer):
        instance = serializer.instance
        new_status = serializer.validated_data.get('status', instance.status)
        if new_status in ('resolved', 'closed') and instance.status not in ('resolved', 'closed'):
            serializer.save(resolved_at=timezone.now())
        else:
            serializer.save()


# ── Contentieux / Disputes ───────────────────────────────────────────────────

@extend_schema(tags=['support'])
class MyDisputeListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        return DisputeSerializer

    def get_queryset(self):
        return Dispute.objects.filter(complainant=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        order = serializer.validated_data.get('order')
        if order is not None and order.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous ne pouvez contester que vos propres commandes.")
        serializer.save(complainant=self.request.user)


@extend_schema(tags=['support'])
class MyDisputeDetailView(generics.RetrieveAPIView):
    serializer_class = DisputeDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Dispute.objects.filter(complainant=self.request.user).prefetch_related(
            'evidences', 'messages'
        )


@extend_schema(tags=['support'])
class DisputeEvidenceCreateView(generics.CreateAPIView):
    serializer_class = DisputeEvidenceSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_create(self, serializer):
        dispute = generics.get_object_or_404(Dispute, pk=self.kwargs['pk'])
        # Seuls le plaignant et l'admin peuvent soumettre des preuves
        if dispute.complainant != self.request.user and self.request.user.role != 'admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()
        if dispute.status in ('resolved_buyer', 'resolved_seller', 'closed'):
            from rest_framework.exceptions import ValidationError
            raise ValidationError('Ce contentieux est clôturé.')
        serializer.save(dispute=dispute, submitted_by=self.request.user)


@extend_schema(tags=['support'])
class DisputeMessageCreateView(generics.CreateAPIView):
    serializer_class = DisputeMessageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        dispute = generics.get_object_or_404(Dispute, pk=self.kwargs['pk'])
        # Seuls le plaignant et l'admin peuvent envoyer des messages
        if dispute.complainant != self.request.user and self.request.user.role != 'admin':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()
        is_internal = serializer.validated_data.get('is_internal', False)
        if is_internal and self.request.user.role != 'admin':
            serializer.validated_data['is_internal'] = False
        serializer.save(dispute=dispute, sender=self.request.user)


# ── Admin contentieux ─────────────────────────────────────────────────────────

@extend_schema(tags=['support'])
class AdminDisputeListView(generics.ListAPIView):
    serializer_class = DisputeSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = Dispute.objects.select_related('complainant', 'defendant_store', 'order')
        st = self.request.query_params.get('status')
        if st:
            qs = qs.filter(status=st)
        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(reference__icontains=search) |
                Q(subject__icontains=search) |
                Q(complainant__email__icontains=search) |
                Q(complainant__first_name__icontains=search)
            )
        return qs.order_by('-created_at')


@extend_schema(tags=['support'])
class AdminDisputeDetailView(generics.RetrieveAPIView):
    serializer_class = DisputeDetailSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = Dispute.objects.prefetch_related('evidences', 'messages')


@extend_schema(tags=['support'])
class AdminDisputeDecisionView(APIView):
    """Admin — rendre une décision sur un contentieux."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        dispute = generics.get_object_or_404(Dispute, pk=pk)
        serializer = DisputeDecisionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_status = serializer.validated_data['status']
        valid_statuses = (
            'resolved_buyer', 'resolved_seller', 'resolved_partial', 'closed', 'escalated'
        )
        if new_status not in valid_statuses:
            return Response(
                {'detail': f'Statut invalide. Autorisés: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dispute.status = new_status
        dispute.amount_awarded = serializer.validated_data.get('amount_awarded', 0)
        dispute.decision_notes = serializer.validated_data.get('decision_notes', '')
        dispute.arbitrator = request.user
        dispute.resolved_at = timezone.now()
        dispute.save()

        # Si résolu en faveur acheteur, rembourser vers wallet
        if new_status == 'resolved_buyer' and dispute.amount_awarded > 0:
            try:
                from apps.wallets.models import Wallet, WalletTransaction
                wallet, _ = Wallet.objects.get_or_create(user=dispute.complainant)
                wallet.balance += dispute.amount_awarded
                wallet.save(update_fields=['balance'])
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='credit',
                    amount=dispute.amount_awarded,
                    description=f'Remboursement contentieux {dispute.reference}',
                    reference=dispute.reference,
                )
            except Exception:
                pass

        return Response(DisputeDetailSerializer(dispute, context={'request': request}).data)
