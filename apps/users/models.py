from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField
from core.models import TimeStampedModel


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('vendor', 'Vendeur'),
        ('customer', 'Client'),
        ('delivery', 'Livreur'),
        ('affiliate', 'Affilié'),
        ('commercial', 'Commercial'),
        ('assistance', 'Assistance'),
    ]

    email = models.EmailField(unique=True)
    phone = PhoneNumberField(blank=True, null=True, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    fcm_token = models.CharField(max_length=255, blank=True)
    language = models.CharField(max_length=10, default='fr')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        db_table = 'users'

    def __str__(self):
        return f'{self.get_full_name() or self.email} ({self.role})'

    @property
    def full_name(self):
        return self.get_full_name() or self.username

    @property
    def is_vendor(self):
        return self.role == 'vendor'

    @property
    def is_admin_user(self):
        return self.role == 'admin'


class OTPCode(TimeStampedModel):
    PURPOSE_CHOICES = [
        ('phone_verify', 'Vérification téléphone'),
        ('email_verify', 'Vérification email'),
        ('password_reset', 'Réinitialisation mot de passe'),
        ('login', 'Connexion'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_codes')
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'otp_codes'
        verbose_name = 'Code OTP'

    def __str__(self):
        return f'OTP {self.code} pour {self.user.email}'

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class Address(TimeStampedModel):
    LABEL_CHOICES = [
        ('home', 'Domicile'),
        ('work', 'Bureau'),
        ('other', 'Autre'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    label = models.CharField(max_length=20, choices=LABEL_CHOICES, default='home')
    full_name = models.CharField(max_length=150)
    phone = PhoneNumberField()
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Côte d\'Ivoire')
    postal_code = models.CharField(max_length=20, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        db_table = 'addresses'
        verbose_name = 'Adresse'

    def __str__(self):
        return f'{self.label} — {self.full_name}, {self.city}'

    def save(self, *args, **kwargs):
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Favorite(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='favorited_by')

    class Meta:
        db_table = 'favorites'
        unique_together = ('user', 'product')

    def __str__(self):
        return f'{self.user.email} ♥ {self.product.name}'


class CommercialProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='commercial_profile')
    categories = models.ManyToManyField('categories.Category', blank=True, related_name='commercials')
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'commercial_profiles'
        verbose_name = 'Profil commercial'

    def __str__(self):
        return f'Commercial: {self.user.get_full_name() or self.user.email}'
