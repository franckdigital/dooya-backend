import random
import string
from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


def _gen_ref(prefix):
    return prefix + ''.join(random.choices(string.digits, k=8))


class FAQCategory(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    icon = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'faq_categories'
        verbose_name = 'Catégorie FAQ'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class FAQ(TimeStampedModel):
    faq_category = models.ForeignKey(
        FAQCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='faqs'
    )
    question = models.CharField(max_length=500)
    answer = models.TextField()
    is_published = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)
    # Utile si la FAQ est liée à un rôle : tous / client / vendeur
    audience = models.CharField(
        max_length=20,
        choices=[('all', 'Tous'), ('customer', 'Client'), ('vendor', 'Vendeur')],
        default='all',
    )

    class Meta:
        db_table = 'faqs'
        verbose_name = 'FAQ'
        ordering = ['order', 'question']

    def __str__(self):
        return self.question


class SupportTicket(TimeStampedModel):
    CATEGORY_CHOICES = [
        ('order', 'Commande'),
        ('payment', 'Paiement'),
        ('delivery', 'Livraison'),
        ('product', 'Produit'),
        ('account', 'Compte'),
        ('technical', 'Technique'),
        ('vendor', 'Vendeur'),
        ('other', 'Autre'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Faible'),
        ('medium', 'Moyen'),
        ('high', 'Élevé'),
        ('urgent', 'Urgent'),
    ]
    STATUS_CHOICES = [
        ('open', 'Ouvert'),
        ('in_progress', 'En cours'),
        ('waiting_customer', 'En attente client'),
        ('resolved', 'Résolu'),
        ('closed', 'Fermé'),
    ]

    reference = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='support_tickets'
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    subject = models.CharField(max_length=300)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_tickets'
    )
    order = models.ForeignKey(
        'orders.Order', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='support_tickets'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    satisfaction_score = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text='1-5 étoiles après résolution'
    )

    class Meta:
        db_table = 'support_tickets'
        verbose_name = 'Ticket support'
        verbose_name_plural = 'Tickets support'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} — {self.subject}'

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = _gen_ref('TKT')
            while SupportTicket.objects.filter(reference=self.reference).exists():
                self.reference = _gen_ref('TKT')
        super().save(*args, **kwargs)


class TicketMessage(TimeStampedModel):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='ticket_messages'
    )
    content = models.TextField()
    is_internal = models.BooleanField(default=False, help_text='Note interne (staff uniquement)')

    class Meta:
        db_table = 'ticket_messages'
        verbose_name = 'Message ticket'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.ticket.reference} — {self.sender}'


class TicketAttachment(models.Model):
    message = models.ForeignKey(TicketMessage, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='support/attachments/')
    filename = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = 'ticket_attachments'
        verbose_name = 'Pièce jointe ticket'


class Dispute(TimeStampedModel):
    """Litige formel entre un client et un vendeur, arbitré par l'admin."""
    STATUS_CHOICES = [
        ('open', 'Ouvert'),
        ('under_review', 'En examen'),
        ('resolved_buyer', 'Résolu en faveur acheteur'),
        ('resolved_seller', 'Résolu en faveur vendeur'),
        ('resolved_partial', 'Résolution partielle'),
        ('closed', 'Fermé'),
        ('escalated', 'Escaladé'),
    ]

    reference = models.CharField(max_length=20, unique=True, editable=False)
    order = models.ForeignKey(
        'orders.Order', on_delete=models.PROTECT, related_name='disputes',
        null=True, blank=True,
    )
    complainant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='disputes_filed'
    )
    defendant_store = models.ForeignKey(
        'vendors.Store', on_delete=models.PROTECT, related_name='disputes',
        null=True, blank=True,
    )
    subject = models.CharField(max_length=300)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

    # Montants
    amount_claimed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_awarded = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Décision
    decision_notes = models.TextField(blank=True)
    arbitrator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='arbitrated_disputes'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'disputes'
        verbose_name = 'Contentieux'
        verbose_name_plural = 'Contentieux'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.reference} — {self.subject}'

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = _gen_ref('DIS')
            while Dispute.objects.filter(reference=self.reference).exists():
                self.reference = _gen_ref('DIS')
        super().save(*args, **kwargs)


class DisputeEvidence(models.Model):
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name='evidences')
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='dispute_evidences'
    )
    description = models.CharField(max_length=500)
    file = models.FileField(upload_to='disputes/evidences/', blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dispute_evidences'
        verbose_name = 'Preuve contentieux'


class DisputeMessage(TimeStampedModel):
    dispute = models.ForeignKey(Dispute, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='dispute_messages'
    )
    content = models.TextField()
    is_internal = models.BooleanField(default=False)

    class Meta:
        db_table = 'dispute_messages'
        verbose_name = 'Message contentieux'
        ordering = ['created_at']
