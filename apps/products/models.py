from django.db import models
from django.conf import settings
from django.utils import timezone
from core.models import TimeStampedModel


class Tag(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=110, unique=True)

    class Meta:
        db_table = 'tags'
        verbose_name = 'Tag'

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    store = models.ForeignKey('vendors.Store', on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(
        'categories.Category', on_delete=models.SET_NULL, null=True, related_name='products'
    )
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=320, unique=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=500, blank=True)

    # ── Prix de base ──────────────────────────────────────────────────────────
    price = models.DecimalField(max_digits=12, decimal_places=2)
    compare_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # ── Remise temporisée ─────────────────────────────────────────────────────
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Pourcentage'),
        ('fixed', 'Montant fixe'),
    ]
    discount_type = models.CharField(
        max_length=15, choices=DISCOUNT_TYPE_CHOICES, null=True, blank=True
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_start = models.DateTimeField(null=True, blank=True)
    discount_end = models.DateTimeField(null=True, blank=True)

    # ── Stock et logistique ───────────────────────────────────────────────────
    sku = models.CharField(max_length=100, blank=True, unique=True, null=True)
    stock = models.PositiveIntegerField(default=0)
    min_stock_alert = models.PositiveIntegerField(default=5)
    weight = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    dimensions = models.JSONField(null=True, blank=True)

    # ── Statuts ───────────────────────────────────────────────────────────────
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_digital = models.BooleanField(default=False)
    allow_installment = models.BooleanField(default=True, verbose_name='Paiement échelonné autorisé')

    # ── Relations ─────────────────────────────────────────────────────────────
    tags = models.ManyToManyField(Tag, blank=True, related_name='products')

    # ── Stats ─────────────────────────────────────────────────────────────────
    views_count = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    reviews_count = models.PositiveIntegerField(default=0)

    # ── SEO ───────────────────────────────────────────────────────────────────
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)

    class Meta:
        db_table = 'products'
        verbose_name = 'Produit'
        verbose_name_plural = 'Produits'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    # ── Propriétés calculées ──────────────────────────────────────────────────

    @property
    def primary_image(self):
        return self.images.filter(is_primary=True).first() or self.images.first()

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def active_discount(self):
        """Retourne la remise active si dans la fenêtre de validité."""
        if not self.discount_value:
            return None
        now = timezone.now()
        if self.discount_start and now < self.discount_start:
            return None
        if self.discount_end and now > self.discount_end:
            return None
        return {'type': self.discount_type, 'value': self.discount_value}

    @property
    def final_price(self):
        """Prix après application de la remise active."""
        discount = self.active_discount
        if not discount:
            return self.price
        if discount['type'] == 'percentage':
            return max(0, self.price * (1 - discount['value'] / 100))
        return max(0, self.price - discount['value'])

    @property
    def discount_percentage(self):
        """Pourcentage de remise par rapport au prix barré ou à la remise active."""
        discount = self.active_discount
        if discount:
            if discount['type'] == 'percentage':
                return int(discount['value'])
            if self.price > 0:
                return round((1 - self.final_price / self.price) * 100)
        if self.compare_price and self.compare_price > self.price:
            return round((1 - self.price / self.compare_price) * 100)
        return 0

    @property
    def is_on_sale(self):
        return self.active_discount is not None or (
            self.compare_price and self.compare_price > self.price
        )


class ProductAttribute(models.Model):
    """Lie un produit à une valeur d'attribut (ex: Couleur=Rouge)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='attribute_values')
    attribute = models.ForeignKey(
        'categories.Attribute', on_delete=models.CASCADE, related_name='product_attributes'
    )
    value = models.ForeignKey(
        'categories.AttributeValue', on_delete=models.CASCADE,
        null=True, blank=True, related_name='product_attributes'
    )
    custom_value = models.CharField(max_length=500, blank=True, help_text='Pour les attributs texte/nombre')

    class Meta:
        db_table = 'product_attributes'
        verbose_name = 'Caractéristique produit'
        unique_together = ('product', 'attribute', 'value')

    def __str__(self):
        val = self.value.value if self.value else self.custom_value
        return f'{self.product.name} — {self.attribute.name}: {val}'

    @property
    def display_value(self):
        return self.value.value if self.value else self.custom_value


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/images/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'product_images'
        ordering = ['-is_primary', 'order']
        verbose_name = 'Image produit'

    def __str__(self):
        return f'{self.product.name} — image {self.order}'

    def save(self, *args, **kwargs):
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    compare_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    attributes = models.JSONField(default=dict, help_text='Ex: {"Couleur": "Rouge", "Taille": "XL"}')
    image = models.ImageField(upload_to='products/variants/', blank=True, null=True)

    class Meta:
        db_table = 'product_variants'
        verbose_name = 'Variante produit'

    def __str__(self):
        return f'{self.product.name} — {self.name}'

    @property
    def final_price(self):
        return self.price

    @property
    def in_stock(self):
        return self.stock > 0


class ProductVideo(models.Model):
    """Vidéo associée à un produit (URL externe ou fichier uploadé)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=200, blank=True)
    # URL externe (YouTube, Vimeo…) OU fichier uploadé
    video_url = models.URLField(blank=True, help_text='Lien YouTube/Vimeo/autre')
    video_file = models.FileField(upload_to='products/videos/', blank=True, null=True)
    thumbnail = models.ImageField(upload_to='products/video_thumbnails/', blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_videos'
        verbose_name = 'Vidéo produit'
        ordering = ['-is_primary', 'order']

    def save(self, *args, **kwargs):
        if self.is_primary:
            ProductVideo.objects.filter(
                product=self.product, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.product.name} — vidéo {self.order}'


class ProductView(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='view_records')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    session_key = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_views'
        verbose_name = 'Vue produit'
