from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from core.permissions import IsAdmin
from core.pagination import StandardPagination
from .models import Wallet, WalletTransaction, WithdrawalRequest
from .serializers import WalletSerializer, WalletTransactionSerializer, WithdrawalRequestSerializer


@extend_schema(tags=['wallets'])
class WalletView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)


@extend_schema(tags=['wallets'])
class WalletTransactionListView(generics.ListAPIView):
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        wallet, _ = Wallet.objects.get_or_create(user=self.request.user)
        qs = wallet.transactions.all()
        txn_type = self.request.query_params.get('type')
        category = self.request.query_params.get('category')
        if txn_type:
            qs = qs.filter(type=txn_type)
        if category:
            qs = qs.filter(category=category)
        return qs.order_by('-created_at')


@extend_schema(tags=['wallets'])
class WithdrawalRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        requests_qs = wallet.withdrawal_requests.all().order_by('-created_at')
        serializer = WithdrawalRequestSerializer(requests_qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        serializer = WithdrawalRequestSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        amount = serializer.validated_data['amount']
        wallet.debit(amount, f"Demande de retrait via {serializer.validated_data['method']}")
        serializer.save(wallet=wallet)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['wallets'])
class AdminWithdrawalListView(generics.ListAPIView):
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = WithdrawalRequest.objects.all().select_related('wallet__user')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by('-created_at')


@extend_schema(tags=['wallets'])
class AdminWithdrawalActionView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        try:
            withdrawal = WithdrawalRequest.objects.get(pk=pk)
        except WithdrawalRequest.DoesNotExist:
            return Response({'detail': 'Demande introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action')
        note = request.data.get('note', '')

        if action == 'approve':
            withdrawal.status = 'approved'
        elif action == 'reject':
            withdrawal.status = 'rejected'
            withdrawal.wallet.credit(withdrawal.amount, 'Remboursement suite à rejet de retrait')
        elif action == 'process':
            withdrawal.status = 'processed'
            withdrawal.processed_at = timezone.now()
        else:
            return Response({'detail': 'Action invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        withdrawal.admin_note = note
        withdrawal.save()
        return Response(WithdrawalRequestSerializer(withdrawal).data)
