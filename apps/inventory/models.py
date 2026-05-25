from django.db import models
from django.conf import settings
from django.utils import timezone
from core.models import TimeStampedModel


class Warehouse(TimeStampedModel):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='CI')
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_warehouses'
    )

    class Meta:
        db_table = 'warehouses'
        verbose_name = 'Entrepôt'

    def __str__(self):
        return f'{self.name} ({self.code})'

    def save(self, *args, **kwargs):
        if self.is_default:
            Warehouse.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class StockLocation(models.Model):
    """Stock d'un produit (ou variante) dans un entrepôt."""
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock_locations')
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE, related_name='stock_locations'
    )
    variant = models.ForeignKey(
        'products.ProductVariant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='stock_locations'
    )
    quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    reorder_point = models.PositiveIntegerField(
        default=10, help_text='Niveau déclenchant un réapprovisionnement automatique'
    )
    reorder_quantity = models.PositiveIntegerField(
        default=50, help_text='Quantité à commander lors du réapprovisionnement'
    )

    class Meta:
        db_table = 'stock_locations'
        verbose_name = 'Emplacement stock'
        unique_together = ('warehouse', 'product', 'variant')

    def __str__(self):
        name = self.variant.name if self.variant else self.product.name
        return f'{name} @ {self.warehouse.code}: {self.quantity}'

    @property
    def available_quantity(self):
        return max(0, self.quantity - self.reserved_quantity)

    @property
    def is_low(self):
        return self.available_quantity <= self.reorder_point


class StockMovement(TimeStampedModel):
    """Traçabilité complète de chaque mouvement de stock."""
    MOVEMENT_TYPE_CHOICES = [
        ('in', 'Entrée'),
        ('out', 'Sortie'),
        ('adjustment', 'Ajustement'),
        ('reservation', 'Réservation'),
        ('release', 'Libération réservation'),
        ('return', 'Retour'),
        ('transfer_in', 'Transfert entrant'),
        ('transfer_out', 'Transfert sortant'),
    ]
    REASON_CHOICES = [
        ('purchase', 'Achat fournisseur'),
        ('sale', 'Vente'),
        ('return_customer', 'Retour client'),
        ('return_supplier', 'Retour fournisseur'),
        ('adjustment_positive', 'Correction positive'),
        ('adjustment_negative', 'Correction négative'),
        ('initial', 'Stock initial'),
        ('cancelled_order', 'Commande annulée'),
        ('reserved_order', 'Réservé pour commande'),
        ('reservation_released', 'Réservation libérée'),
        ('sav_return', 'Retour SAV'),
        ('transfer', 'Transfert inter-entrepôt'),
        ('loss', 'Perte / Casse'),
        ('other', 'Autre'),
    ]

    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE, related_name='stock_movements'
    )
    variant = models.ForeignKey(
        'products.ProductVariant', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='stock_movements'
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, null=True, blank=True, related_name='movements'
    )
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    # Quantité signée : positive = entrée, négative = sortie
    quantity = models.IntegerField()
    stock_before = models.PositiveIntegerField()
    stock_after = models.PositiveIntegerField()
    reference = models.CharField(max_length=100, blank=True, help_text='N° commande, SAV, etc.')
    order = models.ForeignKey(
        'orders.Order', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='stock_movements'
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='stock_movements'
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'stock_movements'
        verbose_name = 'Mouvement de stock'
        verbose_name_plural = 'Mouvements de stock'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.product.name} {self.quantity:+d} ({self.get_reason_display()})'


class StockAlert(TimeStampedModel):
    """Alerte générée automatiquement quand le stock passe sous un seuil."""
    ALERT_TYPE_CHOICES = [
        ('low_stock', 'Stock bas'),
        ('out_of_stock', 'Rupture de stock'),
        ('reorder_point', 'Point de réapprovisionnement atteint'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('acknowledged', 'Prise en compte'),
        ('resolved', 'Résolue'),
    ]

    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE, related_name='stock_alerts'
    )
    variant = models.ForeignKey(
        'products.ProductVariant', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='stock_alerts'
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, null=True, blank=True
    )
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    current_stock = models.PositiveIntegerField()
    threshold = models.PositiveIntegerField()
    message = models.TextField(blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'stock_alerts'
        verbose_name = 'Alerte stock'
        verbose_name_plural = 'Alertes stock'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_alert_type_display()} — {self.product.name} ({self.current_stock})'


class StockReservation(TimeStampedModel):
    """Réservation temporaire de stock lors d'un ajout panier ou création commande."""
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE, related_name='reservations'
    )
    variant = models.ForeignKey(
        'products.ProductVariant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='reservations'
    )
    order = models.ForeignKey(
        'orders.Order', on_delete=models.CASCADE,
        null=True, blank=True, related_name='stock_reservations'
    )
    session_key = models.CharField(max_length=100, blank=True, help_text='Pour les paniers anonymes')
    quantity = models.PositiveIntegerField()
    is_confirmed = models.BooleanField(
        default=False,
        help_text='True = stock définitivement déduit (commande confirmée)'
    )
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'stock_reservations'
        verbose_name = 'Réservation stock'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.product.name} x{self.quantity}'

    @property
    def is_expired(self):
        return not self.is_confirmed and timezone.now() > self.expires_at


class SupplierOrder(TimeStampedModel):
    """Commande fournisseur pour réapprovisionnement."""
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé'),
        ('confirmed', 'Confirmé'),
        ('partial', 'Partiellement reçu'),
        ('completed', 'Complété'),
        ('cancelled', 'Annulé'),
    ]

    reference = models.CharField(max_length=30, unique=True)
    store = models.ForeignKey(
        'vendors.Store', on_delete=models.CASCADE, related_name='supplier_orders'
    )
    # Lien vers le fournisseur homologué (optionnel pour rétro-compatibilité)
    supplier = models.ForeignKey(
        'suppliers.Supplier', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='orders'
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, null=True, blank=True
    )
    supplier_name = models.CharField(max_length=200, blank=True)
    supplier_contact = models.CharField(max_length=200, blank=True)
    supplier_email = models.EmailField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    expected_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        db_table = 'supplier_orders'
        verbose_name = 'Commande fournisseur'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} — {self.supplier_name}'


class SupplierOrderItem(models.Model):
    supplier_order = models.ForeignKey(
        SupplierOrder, on_delete=models.CASCADE, related_name='items'
    )
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    variant = models.ForeignKey(
        'products.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True
    )
    quantity_ordered = models.PositiveIntegerField()
    quantity_received = models.PositiveIntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    is_fully_received = models.BooleanField(default=False)

    class Meta:
        db_table = 'supplier_order_items'
        verbose_name = 'Article commande fournisseur'

    def __str__(self):
        return f'{self.product.name} x{self.quantity_ordered}'

    @property
    def total_cost(self):
        return self.unit_cost * self.quantity_ordered
