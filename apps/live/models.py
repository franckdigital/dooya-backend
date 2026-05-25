import uuid
from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class LiveSession(TimeStampedModel):
    STATUS_CHOICES = [
        ('scheduled', 'Programmée'),
        ('live', 'En direct'),
        ('ended', 'Terminée'),
        ('cancelled', 'Annulée'),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to='live/thumbnails/', blank=True, null=True)
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_live_sessions'
    )
    store = models.ForeignKey(
        'vendors.Store', on_delete=models.CASCADE, related_name='live_sessions'
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='scheduled')
    scheduled_at = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    # Stream identifiers — renseignés par le vendeur ou auto via service externe
    stream_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    stream_url = models.URLField(blank=True, help_text='URL HLS/RTMP fournie par le service de streaming')
    room_id = models.CharField(max_length=100, unique=True, blank=True)

    # Statistiques
    viewer_count = models.PositiveIntegerField(default=0)
    peak_viewer_count = models.PositiveIntegerField(default=0)
    total_orders = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    is_recorded = models.BooleanField(default=False)
    recording_url = models.URLField(blank=True)

    class Meta:
        db_table = 'live_sessions'
        verbose_name = 'Session live'
        ordering = ['-scheduled_at']

    def save(self, *args, **kwargs):
        if not self.room_id:
            self.room_id = f'live_{self.stream_key}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.title} [{self.get_status_display()}]'


class LiveProduct(TimeStampedModel):
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='live_products')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='live_appearances')
    variant = models.ForeignKey(
        'products.ProductVariant', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='live_appearances'
    )
    live_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Prix spécial live (remplace le prix normal si renseigné)'
    )
    discount_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_featured = models.BooleanField(default=False, help_text='Produit actuellement mis en avant')
    position = models.PositiveSmallIntegerField(default=0)
    units_sold = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'live_products'
        verbose_name = 'Produit live'
        ordering = ['position']
        unique_together = ('session', 'product', 'variant')

    def save(self, *args, **kwargs):
        if self.is_featured:
            LiveProduct.objects.filter(session=self.session, is_featured=True).exclude(pk=self.pk).update(is_featured=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.product.name} — {self.session.title}'


class LiveComment(TimeStampedModel):
    REACTION_TYPES = [
        ('comment', 'Commentaire'),
        ('like', 'Like'),
        ('love', 'Love'),
        ('fire', 'Feu'),
        ('clap', 'Applaudissement'),
    ]

    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='live_comments'
    )
    content = models.TextField(blank=True)
    comment_type = models.CharField(max_length=10, choices=REACTION_TYPES, default='comment')
    is_pinned = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'live_comments'
        verbose_name = 'Commentaire live'
        ordering = ['-created_at']

    def __str__(self):
        user = self.user.get_full_name() if self.user else 'Anonyme'
        return f'{user}: {self.content[:50]}'


class LiveViewer(models.Model):
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='viewers')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='live_views'
    )
    session_key = models.CharField(max_length=100, blank=True, help_text='Pour les anonymes')
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'live_viewers'
        verbose_name = 'Spectateur live'

    def __str__(self):
        return f'{self.user or self.session_key} — {self.session.title}'


class LiveOrder(TimeStampedModel):
    """Lie une commande à une session live et au produit mis en avant à ce moment."""
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='live_orders')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='live_order')
    live_product = models.ForeignKey(
        LiveProduct, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders'
    )

    class Meta:
        db_table = 'live_orders'
        verbose_name = 'Commande live'

    def __str__(self):
        return f'Commande {self.order.order_number} — {self.session.title}'
