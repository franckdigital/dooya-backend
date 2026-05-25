from django.db import models
from django.conf import settings
from django.db import transaction
from core.models import TimeStampedModel
from core.utils import generate_reference


class Wallet(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    currency = models.CharField(max_length=5, default='XOF')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'wallets'
        verbose_name = 'Portefeuille'

    def __str__(self):
        return f'{self.user.email} - {self.balance} {self.currency}'

    @transaction.atomic
    def credit(self, amount, description, ref=None):
        if amount <= 0:
            raise ValueError('Le montant doit être positif.')
        balance_before = self.balance
        self.balance += amount
        self.save(update_fields=['balance', 'updated_at'])
        WalletTransaction.objects.create(
            wallet=self,
            type='credit',
            amount=amount,
            balance_before=balance_before,
            balance_after=self.balance,
            reference=ref or generate_reference(),
            description=description,
        )
        return self

    @transaction.atomic
    def debit(self, amount, description, ref=None):
        if amount <= 0:
            raise ValueError('Le montant doit être positif.')
        if self.balance < amount:
            from core.exceptions import InsufficientBalanceError
            raise InsufficientBalanceError(f'Solde insuffisant: {self.balance} < {amount}')
        balance_before = self.balance
        self.balance -= amount
        self.save(update_fields=['balance', 'updated_at'])
        WalletTransaction.objects.create(
            wallet=self,
            type='debit',
            amount=amount,
            balance_before=balance_before,
            balance_after=self.balance,
            reference=ref or generate_reference(),
            description=description,
        )
        return self


class WalletTransaction(models.Model):
    TYPE_CHOICES = [
        ('credit', 'Crédit'),
        ('debit', 'Débit'),
    ]
    CATEGORY_CHOICES = [
        ('order_payment', 'Paiement commande'),
        ('vendor_revenue', 'Revenu vendeur'),
        ('affiliate_commission', 'Commission affilié'),
        ('withdrawal', 'Retrait'),
        ('refund', 'Remboursement'),
        ('bonus', 'Bonus'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    balance_before = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2)
    reference = models.CharField(max_length=50, unique=True, default=generate_reference)
    description = models.CharField(max_length=255)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='order_payment')
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wallet_transactions'
        verbose_name = 'Transaction portefeuille'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.type} {self.amount} - {self.reference}'


class WithdrawalRequest(TimeStampedModel):
    METHOD_CHOICES = [
        ('orange_money', 'Orange Money'),
        ('mtn_money', 'MTN Money'),
        ('wave', 'Wave'),
        ('bank', 'Virement bancaire'),
    ]
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
        ('processed', 'Traité'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='withdrawal_requests')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    account_number = models.CharField(max_length=50)
    account_name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processed_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True)

    class Meta:
        db_table = 'withdrawal_requests'
        verbose_name = 'Demande de retrait'
        ordering = ['-created_at']

    def __str__(self):
        return f'Retrait {self.amount} {self.wallet.currency} - {self.status}'
