from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class Supplier(TimeStampedModel):
    """Fournisseur — partenaire d'approvisionnement d'une ou plusieurs boutiques."""
    RATING_CHOICES = [
        ('A', 'Excellent'),
        ('B', 'Bon'),
        ('C', 'Acceptable'),
        ('D', 'Médiocre'),
        ('F', 'Défaillant'),
    ]

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=30, unique=True)
    contact_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    whatsapp = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='CI')
    website = models.URLField(blank=True)

    # Conditions commerciales
    payment_terms = models.CharField(
        max_length=100, blank=True,
        help_text='Ex: 30 jours net, paiement à la commande…'
    )
    lead_time_days = models.PositiveIntegerField(
        default=7, help_text='Délai de livraison moyen en jours'
    )
    currency = models.CharField(max_length=5, default='XOF')
    min_order_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        help_text='Montant minimum de commande'
    )

    # Qualité globale (calculée automatiquement)
    quality_rating = models.CharField(
        max_length=1, choices=RATING_CHOICES, default='B'
    )
    quality_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=100.00,
        help_text='Score qualité 0-100 mis à jour automatiquement'
    )
    defect_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        help_text='% de livraisons avec défauts'
    )
    on_time_delivery_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=100.00,
        help_text='% de livraisons à temps'
    )

    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(
        default=False, help_text='Fournisseur homologué par l\'admin'
    )
    notes = models.TextField(blank=True)

    # Relations
    managed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_suppliers'
    )

    class Meta:
        db_table = 'suppliers'
        verbose_name = 'Fournisseur'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'


class SupplierProduct(models.Model):
    """Lien fournisseur ↔ produit : prix d'achat, délai, référence fournisseur."""
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name='supplier_products'
    )
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE, related_name='supplier_links'
    )
    variant = models.ForeignKey(
        'products.ProductVariant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='supplier_links'
    )
    supplier_sku = models.CharField(
        max_length=100, blank=True,
        help_text='Référence du produit chez le fournisseur'
    )
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=5, default='XOF')
    min_order_quantity = models.PositiveIntegerField(default=1)
    lead_time_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Override du délai fournisseur pour ce produit'
    )
    is_preferred = models.BooleanField(
        default=False,
        help_text='Fournisseur préféré pour ce produit'
    )
    last_price_update = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = 'supplier_products'
        verbose_name = 'Produit fournisseur'
        unique_together = ('supplier', 'product', 'variant')

    def __str__(self):
        return f'{self.supplier.name} → {self.product.name}'

    def save(self, *args, **kwargs):
        # Un seul fournisseur préféré par produit/variante
        if self.is_preferred:
            SupplierProduct.objects.filter(
                product=self.product, variant=self.variant, is_preferred=True
            ).exclude(pk=self.pk).update(is_preferred=False)
        super().save(*args, **kwargs)


class SupplierContract(TimeStampedModel):
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('active', 'Actif'),
        ('expired', 'Expiré'),
        ('terminated', 'Résilié'),
    ]

    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name='contracts'
    )
    reference = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    terms = models.TextField(blank=True)
    document = models.FileField(
        upload_to='suppliers/contracts/', blank=True, null=True
    )
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='Commission / remise négociée (%)'
    )
    signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='signed_contracts'
    )

    class Meta:
        db_table = 'supplier_contracts'
        verbose_name = 'Contrat fournisseur'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} — {self.supplier.name}'

    @property
    def is_active(self):
        from django.utils import timezone
        today = timezone.now().date()
        if self.status != 'active':
            return False
        if self.end_date and today > self.end_date:
            return False
        return True


class SupplierPerformanceReport(TimeStampedModel):
    """Rapport mensuel de performance d'un fournisseur (généré automatiquement)."""
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name='performance_reports'
    )
    period_year = models.PositiveIntegerField()
    period_month = models.PositiveIntegerField()
    orders_count = models.PositiveIntegerField(default=0)
    orders_completed = models.PositiveIntegerField(default=0)
    orders_late = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    defective_items = models.PositiveIntegerField(default=0)
    total_items_received = models.PositiveIntegerField(default=0)
    quality_score = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    on_time_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'supplier_performance_reports'
        verbose_name = 'Rapport performance fournisseur'
        unique_together = ('supplier', 'period_year', 'period_month')
        ordering = ['-period_year', '-period_month']

    def __str__(self):
        return f'{self.supplier.name} — {self.period_year}/{self.period_month:02d}'

    @property
    def defect_rate(self):
        if not self.total_items_received:
            return 0
        return round(self.defective_items / self.total_items_received * 100, 2)
