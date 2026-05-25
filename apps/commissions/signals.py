from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='orders.Order')
def auto_create_commission(sender, instance, **kwargs):
    """Crée automatiquement la commission quand une commande est complétée."""
    if instance.status == 'completed':
        from .services import create_commission_for_order
        try:
            create_commission_for_order(instance)
        except Exception:
            pass
