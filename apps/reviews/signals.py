from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg


@receiver([post_save, post_delete], sender='reviews.ProductReview')
def update_product_rating(sender, instance, **kwargs):
    from apps.products.models import Product
    from apps.reviews.models import ProductReview
    product = instance.product
    stats = ProductReview.objects.filter(product=product, is_approved=True).aggregate(avg=Avg('rating'))
    product.rating = stats['avg'] or 0
    product.reviews_count = ProductReview.objects.filter(product=product, is_approved=True).count()
    product.save(update_fields=['rating', 'reviews_count'])


@receiver([post_save, post_delete], sender='reviews.StoreReview')
def update_store_rating(sender, instance, **kwargs):
    from apps.vendors.models import Store
    from apps.reviews.models import StoreReview
    store = instance.store
    stats = StoreReview.objects.filter(store=store, is_approved=True).aggregate(avg=Avg('rating'))
    store.rating = stats['avg'] or 0
    store.save(update_fields=['rating'])


@receiver(post_save, sender='reviews.ReviewHelpful')
def update_helpful_count(sender, instance, created, **kwargs):
    if created:
        review = instance.review
        review.helpful_count = review.helpful_votes.count()
        review.save(update_fields=['helpful_count'])


@receiver(post_delete, sender='reviews.ReviewHelpful')
def decrease_helpful_count(sender, instance, **kwargs):
    review = instance.review
    review.helpful_count = review.helpful_votes.count()
    review.save(update_fields=['helpful_count'])
