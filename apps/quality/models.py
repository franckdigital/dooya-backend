import random
import string
from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


def _gen_ref(prefix):
    return prefix + ''.join(random.choices(string.digits, k=8))


class ProductQualityProfile(models.Model):
    """
    Fiche qualité d'un produit — mise à jour automatique après chaque
    inspection ou retour. Note globale calculée sur l'historique.
    """
    GRADE_CHOICES = [
        ('A', 'Excellent (≥95%)'),
        ('B', 'Bon (80-94%)'),
        ('C', 'Acceptable (60-79%)'),
        ('D', 'Médiocre (40-59%)'),
        ('F', 'Défectueux (<40%)'),
    ]

    product = models.OneToOneField(
        'products.Product', on_delete=models.CASCADE, related_name='quality_profile'
    )
    grade = models.CharField(max_length=1, choices=GRADE_CHOICES, default='B')
    quality_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=100.0,
        help_text='Score 0-100 calculé automatiquement'
    )
    defect_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.0,
        help_text='% unités défectueuses sur toutes les inspections'
    )
    return_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.0,
        help_text='% de retours sur les ventes totales'
    )
    total_units_inspected = models.PositiveIntegerField(default=0)
    total_units_defective = models.PositiveIntegerField(default=0)
    total_returns = models.PositiveIntegerField(default=0)
    total_sales = models.PositiveIntegerField(default=0)
    last_inspection_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'product_quality_profiles'
        verbose_name = 'Fiche qualité produit'

    def __str__(self):
        return f'{self.product.name} — Grade {self.grade} ({self.quality_score}%)'

    def recalculate(self):
        """Recalcule le score et la note depuis les inspections."""
        if self.total_units_inspected > 0:
            passed = self.total_units_inspected - self.total_units_defective
            self.quality_score = round(passed / self.total_units_inspected * 100, 2)
            self.defect_rate = round(self.total_units_defective / self.total_units_inspected * 100, 2)
        else:
            self.quality_score = 100.0
            self.defect_rate = 0.0

        if self.total_sales > 0:
            self.return_rate = round(self.total_returns / self.total_sales * 100, 2)

        score = float(self.quality_score)
        if score >= 95:
            self.grade = 'A'
        elif score >= 80:
            self.grade = 'B'
        elif score >= 60:
            self.grade = 'C'
        elif score >= 40:
            self.grade = 'D'
        else:
            self.grade = 'F'

        self.save()


class QualityInspection(TimeStampedModel):
    """Inspection qualité — à la réception fournisseur ou lors d'un retour client."""
    INSPECTION_TYPE_CHOICES = [
        ('reception', 'Réception fournisseur'),
        ('customer_return', 'Retour client'),
        ('periodic', 'Contrôle périodique'),
        ('complaint', 'Suite plainte / contentieux'),
        ('pre_shipment', 'Avant expédition'),
    ]
    RESULT_CHOICES = [
        ('pending', 'En attente'),
        ('passed', 'Conforme'),
        ('failed', 'Non conforme'),
        ('partial', 'Partiellement conforme'),
    ]
    GRADE_CHOICES = ProductQualityProfile.GRADE_CHOICES

    reference = models.CharField(max_length=20, unique=True, editable=False)
    inspection_type = models.CharField(max_length=20, choices=INSPECTION_TYPE_CHOICES)
    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE, related_name='quality_inspections'
    )
    variant = models.ForeignKey(
        'products.ProductVariant', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='quality_inspections'
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='quality_inspections'
    )
    supplier_order_item = models.ForeignKey(
        'inventory.SupplierOrderItem', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='quality_inspections'
    )
    order_item = models.ForeignKey(
        'orders.OrderItem', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='quality_inspections'
    )
    # Lié à un retour produit
    product_return = models.OneToOneField(
        'quality.ProductReturn', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='inspection'
    )
    # Lié à un contentieux
    dispute = models.ForeignKey(
        'support.Dispute', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='quality_inspections'
    )

    quantity_inspected = models.PositiveIntegerField(default=1)
    quantity_passed = models.PositiveIntegerField(default=0)
    quantity_failed = models.PositiveIntegerField(default=0)

    result = models.CharField(max_length=15, choices=RESULT_CHOICES, default='pending')
    grade = models.CharField(max_length=1, choices=GRADE_CHOICES, null=True, blank=True)
    inspection_date = models.DateField(null=True, blank=True)
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='conducted_inspections'
    )
    notes = models.TextField(blank=True)
    # Rapport détaillé
    recommendations = models.TextField(blank=True)

    class Meta:
        db_table = 'quality_inspections'
        verbose_name = 'Inspection qualité'
        verbose_name_plural = 'Inspections qualité'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} — {self.product.name} ({self.get_result_display()})'

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = _gen_ref('QCI')
            while QualityInspection.objects.filter(reference=self.reference).exists():
                self.reference = _gen_ref('QCI')
        super().save(*args, **kwargs)

    @property
    def pass_rate(self):
        if not self.quantity_inspected:
            return 0
        return round(self.quantity_passed / self.quantity_inspected * 100, 1)


class QualityDefect(models.Model):
    """Défaut constaté lors d'une inspection — nature, gravité, quantité."""
    SEVERITY_CHOICES = [
        ('minor', 'Mineur'),
        ('major', 'Majeur'),
        ('critical', 'Critique'),
    ]
    DEFECT_TYPE_CHOICES = [
        ('cosmetic', 'Cosmétique'),
        ('functional', 'Fonctionnel'),
        ('safety', 'Sécurité'),
        ('packaging', 'Emballage'),
        ('labeling', 'Étiquetage'),
        ('missing_parts', 'Pièces manquantes'),
        ('wrong_specs', 'Spécifications incorrectes'),
        ('damage', 'Dommage physique'),
        ('contamination', 'Contamination'),
        ('other', 'Autre'),
    ]

    inspection = models.ForeignKey(
        QualityInspection, on_delete=models.CASCADE, related_name='defects'
    )
    defect_type = models.CharField(max_length=20, choices=DEFECT_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    description = models.TextField()
    quantity_affected = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'quality_defects'
        verbose_name = 'Défaut qualité'

    def __str__(self):
        return f'{self.get_severity_display()} — {self.get_defect_type_display()}'


class QualityInspectionImage(models.Model):
    inspection = models.ForeignKey(
        QualityInspection, on_delete=models.CASCADE, related_name='images'
    )
    image = models.ImageField(upload_to='quality/inspections/')
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'quality_inspection_images'
        ordering = ['order']
        verbose_name = 'Image inspection qualité'


# ─────────────────────────────────────────────────────────────────────────────
#  Retour produit — modèle central orchestre stock, qualité, SAV, contentieux
# ─────────────────────────────────────────────────────────────────────────────

class ProductReturn(TimeStampedModel):
    """
    Retour produit avec images, motif, état du produit et résolution.
    Orchestre automatiquement :
      • Mise à jour du stock en temps réel (inventory.services)
      • Inspection qualité (QualityInspection)
      • Notification fournisseur si défaut d'origine
      • Contentieux si escalade (support.Dispute)
      • Remplacement ou remboursement
    """
    SOURCE_CHOICES = [
        ('customer', 'Client'),
        ('vendor', 'Vendeur'),
        ('supplier', 'Fournisseur'),
    ]
    REASON_CHOICES = [
        ('defective', 'Produit défectueux'),
        ('wrong_item', 'Mauvais article reçu'),
        ('not_as_described', 'Non conforme à la description'),
        ('damaged_delivery', 'Endommagé à la livraison'),
        ('missing_parts', 'Pièces manquantes'),
        ('quality_issue', 'Problème de qualité'),
        ('size_issue', 'Problème de taille/format'),
        ('changed_mind', "Changement d'avis"),
        ('supplier_defect', 'Défaut fournisseur confirmé'),
        ('expired', 'Produit périmé'),
        ('other', 'Autre'),
    ]
    CONDITION_CHOICES = [
        ('sealed', 'Neuf / Non ouvert'),
        ('good', 'Bon état'),
        ('acceptable', 'État acceptable'),
        ('damaged', 'Endommagé'),
        ('defective', 'Défectueux'),
        ('unusable', 'Inutilisable'),
    ]
    STATUS_CHOICES = [
        ('pending', 'En attente de réception'),
        ('received', 'Produit reçu'),
        ('under_inspection', 'En cours d\'inspection'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
        ('replacement_pending', 'Remplacement en cours'),
        ('replacement_sent', 'Remplacement expédié'),
        ('refunded', 'Remboursé'),
        ('restocked', 'Remis en stock'),
        ('disposed', 'Mis au rebut'),
        ('completed', 'Clôturé'),
    ]
    RESOLUTION_CHOICES = [
        ('refund_wallet', 'Remboursement portefeuille'),
        ('refund_original', 'Remboursement moyen original'),
        ('replacement', 'Remplacement produit'),
        ('store_credit', 'Avoir boutique'),
        ('repair', 'Réparation'),
        ('partial_refund', 'Remboursement partiel'),
        ('no_action', 'Aucune action'),
    ]

    reference = models.CharField(max_length=20, unique=True, editable=False)
    source = models.CharField(max_length=15, choices=SOURCE_CHOICES, default='customer')

    # ── Qui retourne ──────────────────────────────────────────────────────────
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='product_returns'
    )

    # ── Ce qui est retourné ───────────────────────────────────────────────────
    product = models.ForeignKey(
        'products.Product', on_delete=models.PROTECT, related_name='product_returns'
    )
    variant = models.ForeignKey(
        'products.ProductVariant', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='product_returns'
    )
    quantity = models.PositiveIntegerField(default=1)

    # ── Contexte ──────────────────────────────────────────────────────────────
    order_item = models.ForeignKey(
        'orders.OrderItem', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='product_returns'
    )
    sav_request = models.ForeignKey(
        'sav.SavRequest', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='product_returns'
    )
    supplier = models.ForeignKey(
        'suppliers.Supplier', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='product_returns'
    )
    supplier_order_item = models.ForeignKey(
        'inventory.SupplierOrderItem', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='product_returns'
    )

    # ── Description du problème (par le déclarant) ────────────────────────────
    reason = models.CharField(max_length=25, choices=REASON_CHOICES)
    description = models.TextField(
        help_text='Description détaillée du problème par le client / vendeur'
    )
    condition = models.CharField(
        max_length=15, choices=CONDITION_CHOICES, default='defective',
        help_text='État constaté du produit retourné'
    )

    # ── Cycle de vie ──────────────────────────────────────────────────────────
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending')
    resolution = models.CharField(
        max_length=20, choices=RESOLUTION_CHOICES, null=True, blank=True
    )
    resolution_notes = models.TextField(blank=True)

    # ── Stock ─────────────────────────────────────────────────────────────────
    stock_updated = models.BooleanField(default=False)
    restock = models.BooleanField(
        default=False,
        help_text='True = remis en stock, False = mis au rebut'
    )

    # ── Remplacement ──────────────────────────────────────────────────────────
    replacement_product = models.ForeignKey(
        'products.Product', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='replacement_returns'
    )
    replacement_variant = models.ForeignKey(
        'products.ProductVariant', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='replacement_returns'
    )
    replacement_tracking = models.CharField(max_length=100, blank=True)

    # ── Remboursement ─────────────────────────────────────────────────────────
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    # ── Contentieux lié ───────────────────────────────────────────────────────
    dispute = models.ForeignKey(
        'support.Dispute', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='product_returns'
    )

    # ── Traitement ────────────────────────────────────────────────────────────
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='processed_returns'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    return_tracking_number = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'product_returns'
        verbose_name = 'Retour produit'
        verbose_name_plural = 'Retours produits'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} — {self.product.name} ({self.get_status_display()})'

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = _gen_ref('RET')
            while ProductReturn.objects.filter(reference=self.reference).exists():
                self.reference = _gen_ref('RET')
        super().save(*args, **kwargs)


class ProductReturnImage(models.Model):
    """
    Images uploadées par le client/vendeur montrant l'état du produit à retourner.
    Upload via multipart/form-data.
    """
    product_return = models.ForeignKey(
        ProductReturn, on_delete=models.CASCADE, related_name='images'
    )
    image = models.ImageField(upload_to='returns/images/%Y/%m/')
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_return_images'
        ordering = ['order']
        verbose_name = 'Image retour produit'


class SupplierQualityNotice(TimeStampedModel):
    """
    Avis de non-conformité envoyé au fournisseur suite à une inspection échouée.
    Lie qualité ↔ fournisseur ↔ stock ↔ contentieux.
    """
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé'),
        ('acknowledged', 'Accusé réception'),
        ('resolved', 'Résolu'),
        ('disputed', 'Contesté'),
        ('closed', 'Clôturé'),
    ]

    reference = models.CharField(max_length=20, unique=True, editable=False)
    supplier = models.ForeignKey(
        'suppliers.Supplier', on_delete=models.PROTECT, related_name='quality_notices'
    )
    inspection = models.ForeignKey(
        QualityInspection, on_delete=models.PROTECT, related_name='supplier_notices'
    )
    product_return = models.ForeignKey(
        ProductReturn, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='supplier_notices'
    )
    # Si le litige est escaladé vers le module contentieux
    dispute = models.ForeignKey(
        'support.Dispute', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='supplier_notices'
    )

    subject = models.CharField(max_length=300)
    description = models.TextField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')

    quantity_defective = models.PositiveIntegerField(default=0)
    claim_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    supplier_response = models.TextField(blank=True)
    supplier_responded_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_quality_notices'
    )

    class Meta:
        db_table = 'supplier_quality_notices'
        verbose_name = 'Avis de non-conformité fournisseur'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} — {self.supplier.name}'

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = _gen_ref('QNC')
            while SupplierQualityNotice.objects.filter(reference=self.reference).exists():
                self.reference = _gen_ref('QNC')
        super().save(*args, **kwargs)
