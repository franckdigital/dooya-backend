from django.db import models
from django.conf import settings
from core.models import TimeStampedModel
from core.utils import generate_tracking_number


class DeliveryZone(models.Model):
    name = models.CharField(max_length=100)
    cities = models.JSONField(default=list)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_kg = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    estimated_days = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'delivery_zones'
        verbose_name = 'Zone de livraison'

    def __str__(self):
        return self.name


class RelayPoint(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="Côte d'Ivoire")
    manager_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    schedule = models.JSONField(default=dict)

    class Meta:
        db_table = 'relay_points'
        verbose_name = 'Point relais'

    def __str__(self):
        return f'{self.name} - {self.city}'


class Delivery(TimeStampedModel):
    TYPE_CHOICES = [
        ('home_delivery', 'Livraison à domicile'),
        ('relay_point', 'Point relais'),
    ]
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('assigned', 'Assigné'),
        ('picked_up', 'Récupéré'),
        ('in_transit', 'En transit'),
        ('delivered', 'Livré'),
        ('failed', 'Échoué'),
    ]

    order = models.OneToOneField('orders.Order', on_delete=models.CASCADE, related_name='delivery')
    delivery_person = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='deliveries',
        limit_choices_to={'role': 'delivery'},
    )
    relay_point = models.ForeignKey(RelayPoint, on_delete=models.SET_NULL, null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='home_delivery')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    tracking_number = models.CharField(max_length=20, unique=True, editable=False)
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    estimated_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateTimeField(null=True, blank=True)
    delivery_address = models.JSONField(null=True, blank=True)
    delivery_notes = models.TextField(blank=True)
    signature_image = models.ImageField(upload_to='deliveries/signatures/', null=True, blank=True)
    qr_code = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'deliveries'
        verbose_name = 'Livraison'
        ordering = ['-created_at']

    def __str__(self):
        return self.tracking_number

    def save(self, *args, **kwargs):
        if not self.tracking_number:
            self.tracking_number = generate_tracking_number()
            while Delivery.objects.filter(tracking_number=self.tracking_number).exists():
                self.tracking_number = generate_tracking_number()
        super().save(*args, **kwargs)


class DeliveryProfile(models.Model):
    VEHICLE_CHOICES = [
        ('moto',    'Moto'),
        ('voiture', 'Voiture'),
        ('velo',    'Vélo'),
        ('pied',    'À pied'),
        ('other',   'Autre'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='delivery_profile',
        limit_choices_to={'role': 'delivery'},
    )
    coverage_zones = models.ManyToManyField(
        DeliveryZone,
        blank=True,
        related_name='delivery_persons',
    )
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_CHOICES, default='moto')
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'delivery_profiles'
        verbose_name = 'Profil livreur'

    def __str__(self):
        return f'Profil — {self.user.get_full_name() or self.user.email}'


class DeliveryHistory(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name='history')
    status = models.CharField(max_length=20)
    location = models.CharField(max_length=255, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'delivery_history'
        verbose_name = 'Historique livraison'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.delivery.tracking_number} → {self.status}'
