from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class Cart(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='carts')
    session_key = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'carts'
        verbose_name = 'Panier'

    def __str__(self):
        return f"Panier {self.user or self.session_key}"

    def total_price(self):
        return sum(item.subtotal() for item in self.items.select_related('product', 'variant').all())

    def items_count(self):
        return self.items.count()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'cart_items'
        verbose_name = 'Article panier'
        unique_together = ('cart', 'product', 'variant')

    def __str__(self):
        return f'{self.quantity}x {self.product.name}'

    def subtotal(self):
        price = self.variant.price if self.variant else self.product.price
        return price * self.quantity
