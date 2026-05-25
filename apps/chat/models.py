from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class Conversation(TimeStampedModel):
    TYPE_CHOICES = [
        ('customer_vendor', 'Client-Vendeur'),
        ('support', 'Support'),
        ('delivery', 'Livraison'),
    ]

    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='customer_vendor')
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='conversations')

    class Meta:
        db_table = 'conversations'
        verbose_name = 'Conversation'
        ordering = ['-updated_at']

    def __str__(self):
        return f'Conversation {self.pk} ({self.type})'

    @property
    def last_message(self):
        return self.messages.order_by('-created_at').first()


class Message(TimeStampedModel):
    TYPE_CHOICES = [
        ('text', 'Texte'),
        ('image', 'Image'),
        ('audio', 'Message vocal'),
        ('file', 'Fichier'),
        ('voice', 'Message vocal'),  # alias pour compatibilité mobile
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(blank=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='text')
    file = models.FileField(upload_to='chat/files/', null=True, blank=True)

    # Champs spécifiques aux messages vocaux
    audio_duration_seconds = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text='Durée du message vocal en secondes'
    )
    audio_waveform = models.JSONField(
        null=True, blank=True,
        help_text='Forme d\'onde encodée pour la visualisation (liste de floats 0-1)'
    )
    transcript = models.TextField(blank=True, help_text='Transcription automatique du message vocal')

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'messages'
        verbose_name = 'Message'
        ordering = ['created_at']

    def __str__(self):
        return f'Message de {self.sender.email} dans conversation {self.conversation.pk}'


class MessageReaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'message_reactions'
        verbose_name = 'Réaction message'
        unique_together = ('message', 'user')

    def __str__(self):
        return f'{self.user.email} {self.emoji} message {self.message.pk}'
