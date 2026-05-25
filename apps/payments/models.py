from django.db import models
from core.models import TimeStampedModel
from core.utils import generate_reference


class Payment(TimeStampedModel):
    METHOD_CHOICES = [
        ('orange_money', 'Orange Money'),
        ('mtn_money', 'MTN Money'),
        ('wave', 'Wave'),
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('wallet', 'Portefeuille'),
    ]
    GATEWAY_CHOICES = [
        ('cinetpay', 'CinetPay'),
        ('paydunya', 'PayDunya'),
        ('flutterwave', 'Flutterwave'),
        ('internal', 'Interne'),
    ]
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('success', 'Succès'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé'),
        ('refunded', 'Remboursé'),
    ]

    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=5, default='XOF')
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    transaction_id = models.CharField(max_length=200, unique=True, null=True, blank=True)
    reference = models.CharField(max_length=50, unique=True, default=generate_reference)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    metadata = models.JSONField(default=dict)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payments'
        verbose_name = 'Paiement'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} - {self.amount} {self.currency} ({self.status})'


class Refund(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
        ('processed', 'Traité'),
    ]

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'refunds'
        verbose_name = 'Remboursement'

    def __str__(self):
        return f'Remboursement {self.amount} pour {self.payment.reference}'


class InstallmentPlan(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'En attente signature'),
        ('active', 'Actif'),
        ('extended', 'Prolongé'),
        ('completed', 'Complété'),
        ('defaulted', 'En défaut'),
        ('forfeited', 'Article saisi'),
    ]
    FREQUENCY_CHOICES = [
        ('weekly', 'Hebdomadaire'),
        ('monthly', 'Mensuel'),
    ]

    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='installment_plans')
    relay_point = models.ForeignKey(
        'deliveries.RelayPoint', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='installment_plans',
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    down_payment = models.DecimalField(max_digits=12, decimal_places=2)
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2)
    installments_count = models.PositiveIntegerField()
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='monthly')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    contract_signed = models.BooleanField(default=False)
    contract_signed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    extension_granted = models.BooleanField(default=False)
    extended_due_date = models.DateField(null=True, blank=True)
    penalty_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    stock_deducted = models.BooleanField(default=False)
    stock_deducted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'installment_plans'
        verbose_name = 'Plan de paiement fractionné'

    def __str__(self):
        return f'Plan {self.order.order_number} - {self.installments_count} versements'


class Installment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('uploaded', 'Preuve envoyée'),
        ('verified', 'Vérifié'),
        ('rejected', 'Rejeté'),
        ('paid', 'Payé'),
        ('overdue', 'En retard'),
    ]

    plan = models.ForeignKey(InstallmentPlan, on_delete=models.CASCADE, related_name='installments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    paid_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=30, blank=True)
    proof_image = models.ImageField(upload_to='installment_proofs/', null=True, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    verified_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='verified_installments',
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'installments'
        verbose_name = 'Versement'
        ordering = ['due_date']

    def __str__(self):
        return f'Versement {self.amount} le {self.due_date}'
