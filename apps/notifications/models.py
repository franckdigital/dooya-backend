from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class Notification(TimeStampedModel):
    TYPE_CHOICES = [
        ('order', 'Commande'),
        ('payment', 'Paiement'),
        ('delivery', 'Livraison'),
        ('review', 'Avis'),
        ('system', 'Système'),
        ('promo', 'Promotion'),
        ('chat', 'Message'),
        ('sav', 'SAV'),
        ('dispute', 'Litige'),
        ('return', 'Retour'),
        ('ticket', 'Ticket Support'),
    ]
    CHANNEL_CHOICES = [
        ('in_app', 'In-App'),
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('push', 'Push'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(default=dict)
    is_read = models.BooleanField(default=False)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='in_app')

    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notification'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} - {self.title}'


class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    email_order = models.BooleanField(default=True)
    email_promo = models.BooleanField(default=True)
    sms_order = models.BooleanField(default=True)
    sms_promo = models.BooleanField(default=False)
    push_order = models.BooleanField(default=True)
    push_promo = models.BooleanField(default=True)
    whatsapp_order = models.BooleanField(default=True)

    class Meta:
        db_table = 'notification_preferences'
        verbose_name = 'Préférences notifications'

    def __str__(self):
        return f'Préférences de {self.user.email}'
