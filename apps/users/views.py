from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.filters import SearchFilter, OrderingFilter
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Address, Favorite, CommercialProfile
from .serializers import (
    UserDetailSerializer, UserUpdateSerializer, AddressSerializer,
    FavoriteSerializer, CommercialProfileSerializer,
)
from core.permissions import IsAdmin, IsCommercial, IsAssistance, IsAdminOrAssistance
from core.pagination import StandardPagination

User = get_user_model()


@extend_schema(tags=['users'])
class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserDetailSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserDetailSerializer(request.user, context={'request': request}).data)


@extend_schema(tags=['users'])
class UserListView(generics.ListAPIView):
    serializer_class = UserDetailSerializer
    permission_classes = [IsAdmin]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    filterset_fields = ['role', 'is_active']

    def get_queryset(self):
        return User.objects.all().order_by('-date_joined')


@extend_schema(tags=['users'])
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserDetailSerializer
    permission_classes = [IsAdmin]
    queryset = User.objects.all()


@extend_schema(tags=['users'])
class AddressListCreateView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


@extend_schema(tags=['users'])
class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


@extend_schema(tags=['users'])
class FavoriteListView(generics.ListAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related('product')


@extend_schema(tags=['users'])
class FavoriteToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, product_id):
        from apps.products.models import Product
        product = generics.get_object_or_404(Product, id=product_id, is_active=True)
        fav, created = Favorite.objects.get_or_create(user=request.user, product=product)
        if not created:
            fav.delete()
            return Response({'favorited': False, 'message': 'Retiré des favoris'})
        return Response({'favorited': True, 'message': 'Ajouté aux favoris'}, status=status.HTTP_201_CREATED)


@extend_schema(tags=['users'])
class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not user.check_password(old_password):
            return Response({'message': 'Ancien mot de passe incorrect'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'message': 'Mot de passe modifié avec succès'})


# ── Admin: gestion des commerciaux ────────────────────────────────────────────

@extend_schema(tags=['commercials'])
class AdminCommercialListCreateView(generics.ListCreateAPIView):
    serializer_class = CommercialProfileSerializer
    permission_classes = [IsAdmin]
    queryset = CommercialProfile.objects.select_related('user').prefetch_related('categories')


@extend_schema(tags=['commercials'])
class AdminCommercialDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CommercialProfileSerializer
    permission_classes = [IsAdmin]
    queryset = CommercialProfile.objects.select_related('user').prefetch_related('categories')

    def perform_destroy(self, instance):
        user = instance.user
        instance.delete()
        user.role = 'customer'
        user.save(update_fields=['role'])


# ── Commercial: tableau de bord ───────────────────────────────────────────────

@extend_schema(tags=['commercials'])
class CommercialOrdersView(APIView):
    permission_classes = [IsCommercial]

    def get(self, request):
        from apps.orders.models import Order
        from apps.orders.serializers import OrderListSerializer as OrderSerializer

        try:
            profile = request.user.commercial_profile
        except CommercialProfile.DoesNotExist:
            return Response({'results': []})

        category_ids = list(profile.categories.values_list('id', flat=True))
        if not category_ids:
            return Response({'results': []})

        from apps.categories.models import Category
        all_ids = set()
        for cat_id in category_ids:
            try:
                cat = Category.objects.get(pk=cat_id)
                all_ids.update(cat.get_descendants(include_self=True).values_list('id', flat=True))
            except Category.DoesNotExist:
                pass

        orders = Order.objects.filter(
            items__product__category_id__in=all_ids
        ).distinct().select_related('user').prefetch_related('items__product')

        status_filter = request.query_params.get('status')
        if status_filter:
            orders = orders.filter(status=status_filter)

        search = request.query_params.get('search', '').strip()
        if search:
            from django.db.models import Q
            orders = orders.filter(
                Q(order_number__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search)
            )

        page = StandardPagination()
        result = page.paginate_queryset(orders, request)

        # Enrich with phone
        serialized = []
        for order in result:
            s = OrderSerializer(order, context={'request': request}).data
            if order.user and order.user.phone:
                s['customer_phone'] = str(order.user.phone)
            else:
                addr = order.shipping_address or {}
                s['customer_phone'] = addr.get('phone', '') or addr.get('phone_number', '')
            serialized.append(s)

        return page.get_paginated_response(serialized)


@extend_schema(tags=['commercials'])
class CommercialOrderDetailView(APIView):
    permission_classes = [IsCommercial]

    def get(self, request, order_number):
        from apps.orders.models import Order
        from apps.orders.serializers import OrderDetailSerializer

        try:
            profile = request.user.commercial_profile
        except CommercialProfile.DoesNotExist:
            return Response({'detail': 'Profil commercial introuvable.'}, status=404)

        from apps.categories.models import Category
        category_ids = list(profile.categories.values_list('id', flat=True))
        all_ids = set()
        for cat_id in category_ids:
            try:
                cat = Category.objects.get(pk=cat_id)
                all_ids.update(cat.get_descendants(include_self=True).values_list('id', flat=True))
            except Category.DoesNotExist:
                pass

        try:
            order = Order.objects.filter(
                order_number=order_number,
                items__product__category_id__in=all_ids
            ).distinct().prefetch_related('items', 'status_history').select_related('user').get()
        except Order.DoesNotExist:
            return Response({'detail': 'Commande introuvable.'}, status=404)

        return Response(OrderDetailSerializer(order, context={'request': request}).data)


@extend_schema(tags=['commercials'])
class CommercialStatsView(APIView):
    permission_classes = [IsCommercial]

    def get(self, request):
        from apps.orders.models import Order
        from django.db.models import Count, Sum

        try:
            profile = request.user.commercial_profile
        except CommercialProfile.DoesNotExist:
            return Response({'orders': 0, 'revenue': 0, 'categories': []})

        category_ids = list(profile.categories.values_list('id', flat=True))

        from apps.categories.models import Category
        all_ids = set()
        for cat_id in category_ids:
            try:
                cat = Category.objects.get(pk=cat_id)
                all_ids.update(cat.get_descendants(include_self=True).values_list('id', flat=True))
            except Category.DoesNotExist:
                pass

        orders = Order.objects.filter(items__product__category_id__in=all_ids).distinct()

        stats = {
            'total_orders': orders.count(),
            'pending': orders.filter(status='pending').count(),
            'confirmed': orders.filter(status='confirmed').count(),
            'delivered': orders.filter(status='delivered').count(),
            'cancelled': orders.filter(status='cancelled').count(),
            'revenue': float(orders.filter(status='delivered').aggregate(
                total=Sum('total_amount'))['total'] or 0),
            'categories': [{'id': c.id, 'name': c.name} for c in profile.categories.all()],
        }
        return Response(stats)


# ── Assistance: accès support ─────────────────────────────────────────────────

@extend_schema(tags=['assistance'])
class AssistanceTicketListView(generics.ListAPIView):
    permission_classes = [IsAdminOrAssistance]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        from apps.support.serializers import SupportTicketSerializer
        return SupportTicketSerializer

    def get_queryset(self):
        from apps.support.models import SupportTicket
        qs = SupportTicket.objects.select_related('user', 'assigned_to')
        for param in ('status', 'category', 'priority'):
            val = self.request.query_params.get(param)
            if val:
                qs = qs.filter(**{param: val})
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(reference__icontains=search) | qs.filter(subject__icontains=search)
        return qs.order_by('-created_at')


@extend_schema(tags=['assistance'])
class AssistanceTicketDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdminOrAssistance]

    def get_serializer_class(self):
        from apps.support.serializers import SupportTicketDetailSerializer
        return SupportTicketDetailSerializer

    def get_queryset(self):
        from apps.support.models import SupportTicket
        return SupportTicket.objects.prefetch_related('messages__attachments')

    def perform_update(self, serializer):
        from django.utils import timezone
        instance = serializer.instance
        new_status = serializer.validated_data.get('status', instance.status)
        if new_status in ('resolved', 'closed') and instance.status not in ('resolved', 'closed'):
            serializer.save(resolved_at=timezone.now(), assigned_to=self.request.user)
        else:
            serializer.save(assigned_to=self.request.user)


@extend_schema(tags=['assistance'])
class AssistanceTicketMessageView(generics.CreateAPIView):
    permission_classes = [IsAdminOrAssistance]

    def get_serializer_class(self):
        from apps.support.serializers import TicketMessageSerializer
        return TicketMessageSerializer

    def perform_create(self, serializer):
        from apps.support.models import SupportTicket
        ticket = generics.get_object_or_404(SupportTicket, pk=self.kwargs['pk'])
        serializer.save(ticket=ticket, sender=self.request.user)


@extend_schema(tags=['assistance'])
class AssistanceDisputeListView(generics.ListAPIView):
    permission_classes = [IsAdminOrAssistance]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        from apps.support.serializers import DisputeSerializer
        return DisputeSerializer

    def get_queryset(self):
        from apps.support.models import Dispute
        qs = Dispute.objects.select_related('complainant', 'defendant_store', 'order')
        st = self.request.query_params.get('status')
        if st:
            qs = qs.filter(status=st)
        return qs.order_by('-created_at')


@extend_schema(tags=['assistance'])
class AssistanceDisputeDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdminOrAssistance]

    def get_serializer_class(self):
        from apps.support.serializers import DisputeDetailSerializer
        return DisputeDetailSerializer

    def get_queryset(self):
        from apps.support.models import Dispute
        return Dispute.objects.prefetch_related('evidences', 'messages')


@extend_schema(tags=['assistance'])
class AssistanceReviewListView(generics.ListAPIView):
    permission_classes = [IsAdminOrAssistance]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        from apps.reviews.serializers import ProductReviewSerializer
        return ProductReviewSerializer

    def get_queryset(self):
        from apps.reviews.models import ProductReview
        from django.db.models import Q
        qs = ProductReview.objects.select_related('user', 'product').prefetch_related('images')
        approved = self.request.query_params.get('approved')
        if approved is not None:
            qs = qs.filter(is_approved=approved == 'true')
        rating = self.request.query_params.get('rating')
        if rating:
            qs = qs.filter(rating=rating)
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(Q(user__email__icontains=search) | Q(product__name__icontains=search) | Q(body__icontains=search))
        return qs.order_by('-created_at')


@extend_schema(tags=['assistance'])
class AssistanceSavListView(generics.ListAPIView):
    permission_classes = [IsAdminOrAssistance]
    pagination_class = StandardPagination

    def get_serializer_class(self):
        from apps.sav.serializers import SavRequestAdminSerializer
        return SavRequestAdminSerializer

    def get_queryset(self):
        from apps.sav.models import SavRequest
        from django.db.models import Q
        qs = SavRequest.objects.select_related('user', 'order', 'order_item').prefetch_related('images', 'messages')
        st = self.request.query_params.get('status')
        if st:
            qs = qs.filter(status=st)
        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(Q(reference__icontains=search) | Q(user__email__icontains=search))
        return qs.order_by('-created_at')


@extend_schema(tags=['assistance'])
class AssistanceStatsView(APIView):
    permission_classes = [IsAdminOrAssistance]

    def get(self, request):
        from apps.support.models import SupportTicket, Dispute
        from apps.sav.models import SavRequest
        from apps.reviews.models import ProductReview

        return Response({
            'tickets': {
                'total': SupportTicket.objects.count(),
                'open': SupportTicket.objects.filter(status='open').count(),
                'in_progress': SupportTicket.objects.filter(status='in_progress').count(),
                'resolved': SupportTicket.objects.filter(status__in=['resolved', 'closed']).count(),
            },
            'disputes': {
                'total': Dispute.objects.count(),
                'open': Dispute.objects.filter(status__in=['open', 'under_review']).count(),
                'resolved': Dispute.objects.filter(status__in=['resolved_buyer', 'resolved_seller', 'resolved_partial', 'closed']).count(),
            },
            'sav': {
                'total': SavRequest.objects.count(),
                'pending': SavRequest.objects.filter(status='pending').count(),
            },
            'reviews': {
                'total': ProductReview.objects.count(),
                'pending_approval': ProductReview.objects.filter(is_approved=False).count(),
            },
        })


@extend_schema(tags=['assistance'])
class AssistanceSavDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdminOrAssistance]

    def get_serializer_class(self):
        from apps.sav.serializers import SavRequestAdminSerializer
        return SavRequestAdminSerializer

    def get_queryset(self):
        from apps.sav.models import SavRequest
        return SavRequest.objects.prefetch_related('images', 'messages__attachments', 'messages__sender')


@extend_schema(tags=['assistance'])
class AssistanceSavResolveView(APIView):
    permission_classes = [IsAdminOrAssistance]

    def post(self, request, pk):
        from django.utils import timezone as tz
        from apps.sav.models import SavRequest, SavMessage
        from apps.sav.serializers import SavRequestAdminSerializer

        sav = generics.get_object_or_404(SavRequest, pk=pk)
        new_status = request.data.get('status')
        allowed = ('approved', 'rejected', 'processing', 'completed')
        if new_status not in allowed:
            return Response({'detail': f'Statut invalide. Valeurs: {allowed}'}, status=status.HTTP_400_BAD_REQUEST)

        notes = request.data.get('resolution_notes', '').strip()
        sav.status = new_status
        if notes:
            sav.resolution_notes = notes
        sav.resolved_by = request.user
        sav.resolved_at = tz.now()
        sav.save()

        label_map = {'approved': 'Approuvé', 'rejected': 'Rejeté', 'processing': 'En traitement', 'completed': 'Terminé'}
        body = f"[DÉCISION: {label_map.get(new_status, new_status)}]"
        if notes:
            body += f"\n{notes}"
        SavMessage.objects.create(request=sav, sender=request.user, content=body, is_internal=False)

        sav.refresh_from_db()
        return Response(SavRequestAdminSerializer(sav, context={'request': request}).data)


@extend_schema(tags=['assistance'])
class AssistanceSavMessageView(generics.CreateAPIView):
    permission_classes = [IsAdminOrAssistance]

    def get_serializer_class(self):
        from apps.sav.serializers import SavMessageSerializer
        return SavMessageSerializer

    def perform_create(self, serializer):
        from apps.sav.models import SavRequest
        sav = generics.get_object_or_404(SavRequest, pk=self.kwargs['pk'])
        serializer.save(request=sav, sender=self.request.user)


@extend_schema(tags=['assistance'])
class AssistanceReviewApproveView(APIView):
    permission_classes = [IsAdminOrAssistance]

    def post(self, request, pk):
        from apps.reviews.models import ProductReview
        from apps.reviews.serializers import ProductReviewSerializer

        review = generics.get_object_or_404(ProductReview, pk=pk)
        action = request.data.get('action')
        if action == 'approve':
            review.is_approved = True
        elif action == 'reject':
            review.is_approved = False
        else:
            return Response({'detail': 'action must be approve or reject'}, status=status.HTTP_400_BAD_REQUEST)
        review.save(update_fields=['is_approved'])
        return Response(ProductReviewSerializer(review, context={'request': request}).data)


@extend_schema(tags=['assistance'])
class AssistanceDisputeMessageView(generics.CreateAPIView):
    permission_classes = [IsAdminOrAssistance]

    def get_serializer_class(self):
        from apps.support.serializers import DisputeMessageSerializer
        return DisputeMessageSerializer

    def perform_create(self, serializer):
        from apps.support.models import Dispute
        dispute = generics.get_object_or_404(Dispute, pk=self.kwargs['pk'])
        serializer.save(dispute=dispute, sender=self.request.user)


class AssistanceDisputeDecisionView(APIView):
    """Assistance — rendre une décision ou changer le statut d'un litige."""
    permission_classes = [IsAdminOrAssistance]

    def post(self, request, pk):
        from apps.support.models import Dispute
        from apps.support.serializers import DisputeDetailSerializer, DisputeDecisionSerializer
        from django.utils import timezone

        dispute = generics.get_object_or_404(Dispute, pk=pk)
        serializer = DisputeDecisionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        new_status = serializer.validated_data['status']
        valid_statuses = ('resolved_buyer', 'resolved_seller', 'resolved_partial', 'closed', 'escalated', 'under_review')
        if new_status not in valid_statuses:
            return Response({'detail': f'Statut invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        dispute.status = new_status
        if new_status != 'under_review':
            dispute.amount_awarded = serializer.validated_data.get('amount_awarded', 0)
            dispute.decision_notes = serializer.validated_data.get('decision_notes', '')
            dispute.arbitrator = request.user
            dispute.resolved_at = timezone.now()
        dispute.save()

        if new_status == 'resolved_buyer' and dispute.amount_awarded > 0:
            try:
                from apps.wallets.models import Wallet, WalletTransaction
                wallet, _ = Wallet.objects.get_or_create(user=dispute.complainant)
                wallet.balance += dispute.amount_awarded
                wallet.save(update_fields=['balance'])
                WalletTransaction.objects.create(
                    wallet=wallet, transaction_type='credit', amount=dispute.amount_awarded,
                    description=f'Remboursement contentieux {dispute.reference}',
                    reference=dispute.reference,
                )
            except Exception:
                pass

        return Response(DisputeDetailSerializer(dispute, context={'request': request}).data)
