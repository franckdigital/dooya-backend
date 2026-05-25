import random
import string
from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


def generate_sav_reference():
    return 'SAV' + ''.join(random.choices(string.digits, k=8))


class SavRequest(TimeStampedModel):
    TYPE_CHOICES = [
        ('return', 'Retour'),
        ('exchange', 'Échange'),
        ('repair', 'Réparation'),
    ]
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
        ('processing', 'En traitement'),
        ('completed', 'Complété'),
        ('cancelled', 'Annulé'),
    ]
    REASON_CHOICES = [
        ('defective', 'Produit défectueux'),
        ('wrong_item', 'Mauvais article reçu'),
        ('not_as_described', 'Non conforme à la description'),
        ('damaged', 'Endommagé à la livraison'),
        ('size_issue', 'Problème de taille/format'),
        ('changed_mind', "Changement d'avis"),
        ('missing_parts', 'Pièces manquantes'),
        ('other', 'Autre'),
    ]
    REFUND_METHOD_CHOICES = [
        ('wallet', 'Portefeuille'),
        ('original_payment', 'Moyen de paiement original'),
        ('bank_transfer', 'Virement bancaire'),
    ]

    reference = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sav_requests'
    )
    order = models.ForeignKey('orders.Order', on_delete=models.PROTECT, related_name='sav_requests')
    order_item = models.ForeignKey(
        'orders.OrderItem', on_delete=models.PROTECT, related_name='sav_requests'
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Pour échange
    exchange_product = models.ForeignKey(
        'products.Product', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='exchange_requests'
    )
    exchange_variant = models.ForeignKey(
        'products.ProductVariant', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='exchange_requests'
    )

    # Résolution
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='resolved_sav_requests'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    # Remboursement
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    refund_method = models.CharField(
        max_length=20, choices=REFUND_METHOD_CHOICES, blank=True
    )
    refunded_at = models.DateTimeField(null=True, blank=True)

    # Suivi retour physique
    return_tracking_number = models.CharField(max_length=100, blank=True)
    return_received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'sav_requests'
        verbose_name = 'Demande SAV'
        verbose_name_plural = 'Demandes SAV'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} — {self.get_type_display()}'

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = generate_sav_reference()
            while SavRequest.objects.filter(reference=self.reference).exists():
                self.reference = generate_sav_reference()
        super().save(*args, **kwargs)


class SavRequestImage(models.Model):
    request = models.ForeignKey(SavRequest, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='sav/images/')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'sav_request_images'
        ordering = ['order']
        verbose_name = 'Image SAV'


class SavMessage(TimeStampedModel):
    request = models.ForeignKey(SavRequest, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='sav_messages'
    )
    content = models.TextField()
    is_internal = models.BooleanField(
        default=False, help_text='Note interne visible uniquement par le staff'
    )

    class Meta:
        db_table = 'sav_messages'
        verbose_name = 'Message SAV'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.request.reference} — {self.sender}'


class SavMessageAttachment(models.Model):
    message = models.ForeignKey(SavMessage, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='sav/attachments/')
    filename = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'sav_message_attachments'
        verbose_name = 'Pièce jointe SAV'
