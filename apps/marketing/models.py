from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class Campaign(TimeStampedModel):
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('whatsapp', 'WhatsApp'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('scheduled', 'Programmée'),
        ('sending', 'En cours d\'envoi'),
        ('sent', 'Envoyée'),
        ('cancelled', 'Annulée'),
    ]
    AUDIENCE_CHOICES = [
        ('all', 'Tous les utilisateurs'),
        ('customers', 'Clients (ont commandé)'),
        ('vendors', 'Vendeurs'),
        ('inactive', 'Inactifs (>30 jours sans commande)'),
        ('new', 'Nouveaux inscrits (<7 jours)'),
        ('segment', 'Segment personnalisé'),
    ]

    name = models.CharField(max_length=300)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')
    audience = models.CharField(max_length=15, choices=AUDIENCE_CHOICES, default='all')

    subject = models.CharField(max_length=500, blank=True, help_text='Objet email')
    content = models.TextField(help_text='Corps du message / HTML email')
    cta_url = models.URLField(blank=True, help_text='Lien bouton appel à action')
    cta_label = models.CharField(max_length=100, blank=True, default='Voir les offres')

    scheduled_at = models.DateTimeField(null=True, blank=True, help_text='Laisser vide pour envoi immédiat')
    sent_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='marketing_campaigns'
    )

    # Stats
    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    opened_count = models.PositiveIntegerField(default=0)
    clicked_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'marketing_campaigns'
        verbose_name = 'Campagne'
        verbose_name_plural = 'Campagnes'
        ordering = ['-created_at']

    @property
    def open_rate(self):
        if self.sent_count:
            return round(self.opened_count / self.sent_count * 100, 2)
        return 0.0

    @property
    def click_rate(self):
        if self.sent_count:
            return round(self.clicked_count / self.sent_count * 100, 2)
        return 0.0

    def __str__(self):
        return f'{self.name} [{self.get_channel_display()}]'


class CampaignRecipient(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('sent', 'Envoyé'),
        ('opened', 'Ouvert'),
        ('clicked', 'Cliqué'),
        ('failed', 'Échec'),
        ('unsubscribed', 'Désabonné'),
    ]

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='recipients')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='campaign_receipts'
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = 'marketing_campaign_recipients'
        verbose_name = 'Destinataire campagne'
        unique_together = ('campaign', 'user')

    def __str__(self):
        return f'{self.campaign.name} → {self.user.email}'


class AbandonedCartReminder(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('sent', 'Envoyé'),
        ('converted', 'Converti'),
        ('expired', 'Expiré'),
    ]

    cart = models.ForeignKey('cart.Cart', on_delete=models.CASCADE, related_name='reminders')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart_reminders'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reminder_count = models.PositiveSmallIntegerField(default=0)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    cart_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = 'marketing_abandoned_cart_reminders'
        verbose_name = 'Relance panier abandonné'
        unique_together = ('cart', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f'Panier abandonné — {self.user.email}'


class Unsubscribe(models.Model):
    """Opt-out global ou par canal."""
    CHANNEL_CHOICES = Campaign.CHANNEL_CHOICES + [('all', 'Tous')]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='unsubscribes'
    )
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='all')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'marketing_unsubscribes'
        verbose_name = 'Désabonnement'
        unique_together = ('user', 'channel')

    def __str__(self):
        return f'{self.user.email} → {self.channel}'
