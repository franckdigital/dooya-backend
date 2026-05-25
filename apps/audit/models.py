from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class MonthlySnapshot(TimeStampedModel):
    """
    Snapshot mensuel de tous les KPIs.
    Calculé automatiquement le 1er du mois suivant par Celery.
    Sert de base pour les comparaisons M vs M-1 instantanées.
    """
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()  # 1–12
    # null = marketplace global ; sinon snapshot par boutique
    store = models.ForeignKey(
        'vendors.Store', on_delete=models.CASCADE,
        null=True, blank=True, related_name='monthly_snapshots'
    )

    # ── Ventes ────────────────────────────────────────────────────────────────
    revenue = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    orders_total = models.PositiveIntegerField(default=0)
    orders_completed = models.PositiveIntegerField(default=0)
    orders_cancelled = models.PositiveIntegerField(default=0)
    orders_refunded = models.PositiveIntegerField(default=0)
    orders_pending = models.PositiveIntegerField(default=0)
    average_order_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    commissions = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    conversion_rate = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        help_text='Commandes complétées / total commandes (%)'
    )

    # ── Clients ───────────────────────────────────────────────────────────────
    new_customers = models.PositiveIntegerField(default=0)
    returning_customers = models.PositiveIntegerField(default=0)
    total_active_customers = models.PositiveIntegerField(default=0)
    cart_abandonment_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    avg_purchase_frequency = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # ── Produits ──────────────────────────────────────────────────────────────
    units_sold = models.PositiveIntegerField(default=0)
    unique_products_sold = models.PositiveIntegerField(default=0)
    stockout_products = models.PositiveIntegerField(default=0)

    # ── Qualité & Retours ─────────────────────────────────────────────────────
    returns_count = models.PositiveIntegerField(default=0)
    return_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    disputes_opened = models.PositiveIntegerField(default=0)
    disputes_resolved = models.PositiveIntegerField(default=0)
    failed_inspections = models.PositiveIntegerField(default=0)

    # ── Livraison ─────────────────────────────────────────────────────────────
    avg_delivery_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    on_time_delivery_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # ── Satisfaction ──────────────────────────────────────────────────────────
    avg_product_rating = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    reviews_count = models.PositiveIntegerField(default=0)
    support_tickets = models.PositiveIntegerField(default=0)
    avg_ticket_resolution_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'audit_monthly_snapshots'
        verbose_name = 'Snapshot mensuel'
        unique_together = ('year', 'month', 'store')
        ordering = ['-year', '-month']

    def __str__(self):
        scope = self.store.name if self.store else 'Global'
        return f'{scope} — {self.year}/{self.month:02d}'


class KPIAlert(TimeStampedModel):
    """
    Alerte générée automatiquement quand un KPI dépasse ou chute
    en dessous d'un seuil, ou varie de plus de X% vs M-1.
    """
    SEVERITY_CHOICES = [
        ('info', 'Information'),
        ('warning', 'Avertissement'),
        ('critical', 'Critique'),
    ]
    CATEGORY_CHOICES = [
        ('sales', 'Ventes'),
        ('customers', 'Clients'),
        ('products', 'Produits'),
        ('vendors', 'Vendeurs'),
        ('quality', 'Qualité'),
        ('delivery', 'Livraison'),
        ('finance', 'Finance'),
        ('support', 'Support'),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField()
    recommendations = models.TextField(blank=True)
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    metric_name = models.CharField(max_length=100)
    current_value = models.DecimalField(max_digits=16, decimal_places=4, default=0)
    previous_value = models.DecimalField(max_digits=16, decimal_places=4, default=0)
    variation_pct = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    threshold = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    store = models.ForeignKey(
        'vendors.Store', on_delete=models.CASCADE,
        null=True, blank=True, related_name='kpi_alerts'
    )
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='acknowledged_kpi_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'audit_kpi_alerts'
        verbose_name = 'Alerte KPI'
        verbose_name_plural = 'Alertes KPI'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.get_severity_display()}] {self.title}'


class AuditReport(TimeStampedModel):
    """
    Rapport d'audit généré à la demande ou automatiquement chaque mois.
    Stocke les métriques serialisées + résumé textuel + fichier PDF optionnel.
    """
    REPORT_TYPE_CHOICES = [
        ('monthly', 'Rapport mensuel complet'),
        ('sales', 'Analyse ventes'),
        ('customers', 'Comportement client'),
        ('vendors', 'Performance vendeurs'),
        ('products', 'Performance produits'),
        ('quality', 'Qualité & Retours'),
        ('delivery', 'Livraison'),
        ('comparison', 'Comparaison M vs M-1'),
    ]

    title = models.CharField(max_length=300)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    compare_year = models.PositiveSmallIntegerField(null=True, blank=True)
    compare_month = models.PositiveSmallIntegerField(null=True, blank=True)
    store = models.ForeignKey(
        'vendors.Store', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='audit_reports'
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='audit_reports'
    )
    data = models.JSONField(default=dict, help_text='Toutes les métriques sérialisées')
    summary = models.TextField(blank=True, help_text='Résumé narratif auto-généré')
    key_insights = models.JSONField(default=list, help_text='Liste des insights clés')
    is_auto = models.BooleanField(default=False)
    pdf_file = models.FileField(upload_to='audit/reports/', blank=True, null=True)

    class Meta:
        db_table = 'audit_reports'
        verbose_name = 'Rapport audit'
        verbose_name_plural = 'Rapports audit'
        ordering = ['-created_at']

    def __str__(self):
        scope = self.store.name if self.store else 'Global'
        return f'{self.title} — {scope} {self.year}/{self.month:02d}'
