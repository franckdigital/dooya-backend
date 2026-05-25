from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class Report(TimeStampedModel):
    TYPE_CHOICES = [
        ('sales', 'Ventes'),
        ('vendors', 'Vendeurs'),
        ('products', 'Produits'),
        ('payments', 'Paiements'),
        ('users', 'Utilisateurs'),
    ]
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En traitement'),
        ('ready', 'Prêt'),
        ('failed', 'Échoué'),
    ]

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    name = models.CharField(max_length=200)
    parameters = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file = models.FileField(upload_to='reports/', null=True, blank=True)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports')
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'reports'
        verbose_name = 'Rapport'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.type}) - {self.status}'
