from rest_framework import serializers
from django.conf import settings
from .models import Wallet, WalletTransaction, WithdrawalRequest


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ['id', 'type', 'amount', 'balance_before', 'balance_after', 'reference', 'description', 'category', 'metadata', 'created_at']


class WalletSerializer(serializers.ModelSerializer):
    recent_transactions = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ['id', 'balance', 'currency', 'is_active', 'recent_transactions', 'updated_at']

    def get_recent_transactions(self, obj):
        txns = obj.transactions.all()[:10]
        return WalletTransactionSerializer(txns, many=True).data


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='wallet.user.email', read_only=True)

    class Meta:
        model = WithdrawalRequest
        fields = ['id', 'user_name', 'user_email', 'amount', 'method', 'account_number', 'account_name', 'status', 'processed_at', 'admin_note', 'created_at']
        read_only_fields = ['user_name', 'user_email', 'status', 'processed_at', 'admin_note', 'created_at']

    def get_user_name(self, obj):
        try:
            return obj.wallet.user.get_full_name() or obj.wallet.user.email
        except Exception:
            return None

    def validate_amount(self, value):
        min_withdrawal = getattr(settings, 'MARKETPLACE_MIN_WITHDRAWAL', 5000)
        if value < min_withdrawal:
            raise serializers.ValidationError(f'Le montant minimum de retrait est {min_withdrawal} XOF.')
        request = self.context.get('request')
        if request and request.user:
            try:
                wallet = request.user.wallet
                if value > wallet.balance:
                    raise serializers.ValidationError('Solde insuffisant.')
            except Exception:
                pass
        return value
