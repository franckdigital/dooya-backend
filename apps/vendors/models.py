from django.db import models
from django.conf import settings
from phonenumber_field.modelfields import PhoneNumberField
from core.models import TimeStampedModel


class Store(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('active', 'Actif'),
        ('suspended', 'Suspendu'),
        ('rejected', 'Rejeté'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='store')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='stores/logos/', blank=True, null=True)
    banner = models.ImageField(upload_to='stores/banners/', blank=True, null=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="Côte d'Ivoire")
    phone = PhoneNumberField(blank=True, null=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.10)
    is_certified = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_sales = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)

    class Meta:
        db_table = 'stores'
        verbose_name = 'Boutique'
        verbose_name_plural = 'Boutiques'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class StoreDocument(TimeStampedModel):
    DOCUMENT_TYPE_CHOICES = [
        ('id_card', "Carte d'identité"),
        ('business_reg', 'Registre de commerce'),
        ('tax_cert', 'Attestation fiscale'),
    ]

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to='stores/documents/')
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = 'store_documents'
        verbose_name = 'Document boutique'

    def __str__(self):
        return f'{self.store.name} - {self.get_document_type_display()}'


class BankAccount(TimeStampedModel):
    store = models.OneToOneField(Store, on_delete=models.CASCADE, related_name='bank_account')
    bank_name = models.CharField(max_length=100)
    account_name = models.CharField(max_length=200)
    account_number = models.CharField(max_length=50)
    iban = models.CharField(max_length=34, blank=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        db_table = 'bank_accounts'
        verbose_name = 'Compte bancaire'

    def __str__(self):
        return f'{self.store.name} - {self.bank_name}'
