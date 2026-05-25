from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class CommissionRule(TimeStampedModel):
    """
    Règle de commission applicable à une boutique ou une catégorie.
    Priorité : boutique > catégorie > taux global par défaut.
    """
    store = models.OneToOneField(
        'vendors.Store', on_delete=models.CASCADE,
        null=True, blank=True, related_name='commission_rule',
    )
    category = models.ForeignKey(
        'categories.Category', on_delete=models.CASCADE,
        null=True, blank=True, related_name='commission_rules',
    )
    rate = models.DecimalField(
        max_digits=5, decimal_places=4,
        help_text='Taux décimal, ex: 0.10 = 10%'
    )
    flat_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text='Frais fixe par commande (en plus du taux)'
    )
    min_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text='Montant minimum de commande pour appliquer cette règle'
    )
    is_active = models.BooleanField(default=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = 'commission_rules'
        verbose_name = 'Règle de commission'

    def __str__(self):
        target = self.store.name if self.store else (self.category.name if self.category else 'Globale')
        return f'{target} — {float(self.rate)*100:.1f}% + {self.flat_fee} FCFA'


class Commission(TimeStampedModel):
    """Enregistrement de commission calculée pour chaque commande complétée."""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('paid', 'Payée'),
        ('cancelled', 'Annulée'),
    ]

    order = models.OneToOneField(
        'orders.Order', on_delete=models.CASCADE, related_name='commission'
    )
    store = models.ForeignKey(
        'vendors.Store', on_delete=models.CASCADE, related_name='commissions'
    )
    rule = models.ForeignKey(
        CommissionRule, on_delete=models.SET_NULL, null=True, blank=True
    )

    order_amount = models.DecimalField(max_digits=14, decimal_places=2)
    rate_applied = models.DecimalField(max_digits=5, decimal_places=4)
    flat_fee_applied = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    vendor_amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        help_text='Montant dû au vendeur = order_amount - commission_amount'
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    paid_at = models.DateTimeField(null=True, blank=True)
    payout = models.ForeignKey(
        'VendorPayout', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='commissions'
    )

    class Meta:
        db_table = 'commissions'
        verbose_name = 'Commission'
        ordering = ['-created_at']

    def __str__(self):
        return f'Commission {self.order.order_number} — {self.commission_amount} FCFA'


class VendorPayout(TimeStampedModel):
    """Reversement groupé à un vendeur couvrant plusieurs commissions."""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En cours'),
        ('paid', 'Payé'),
        ('failed', 'Échoué'),
    ]
    METHOD_CHOICES = [
        ('bank_transfer', 'Virement bancaire'),
        ('mobile_money', 'Mobile Money'),
        ('wallet', 'Portefeuille interne'),
    ]

    store = models.ForeignKey(
        'vendors.Store', on_delete=models.CASCADE, related_name='payouts'
    )
    reference = models.CharField(max_length=30, unique=True)
    period_start = models.DateField()
    period_end = models.DateField()
    total_order_amount = models.DecimalField(max_digits=14, decimal_places=2)
    total_commission = models.DecimalField(max_digits=12, decimal_places=2)
    total_payout = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    method = models.CharField(max_length=15, choices=METHOD_CHOICES, default='bank_transfer')
    payment_reference = models.CharField(max_length=100, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='processed_payouts'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'vendor_payouts'
        verbose_name = 'Reversement vendeur'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.reference:
            import uuid
            self.reference = f'PAY{uuid.uuid4().hex[:8].upper()}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.reference} — {self.store.name} — {self.total_payout} FCFA'
