from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from core.models import TimeStampedModel


class ProductReview(TimeStampedModel):
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_reviews')
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    helpful_count = models.PositiveIntegerField(default=0)

    # Réponse du vendeur
    vendor_reply = models.TextField(blank=True)
    vendor_replied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'product_reviews'
        verbose_name = 'Avis produit'
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} → {self.product.name} ({self.rating}/5)'


class ReviewImage(models.Model):
    """Photos jointes à un avis client."""
    review = models.ForeignKey(ProductReview, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='reviews/')
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'review_images'
        ordering = ['order']

    def __str__(self):
        return f'Photo avis #{self.review_id}'


class StoreReview(TimeStampedModel):
    store = models.ForeignKey('vendors.Store', on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='store_reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)

    class Meta:
        db_table = 'store_reviews'
        verbose_name = 'Avis boutique'
        unique_together = ('store', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} → {self.store.name} ({self.rating}/5)'


class ReviewHelpful(models.Model):
    review = models.ForeignKey(ProductReview, on_delete=models.CASCADE, related_name='helpful_votes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'review_helpful'
        verbose_name = 'Vote utile'
        unique_together = ('review', 'user')
