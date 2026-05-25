import random
import string
from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


def generate_affiliate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


class AffiliateProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='affiliate_profile')
    code = models.CharField(max_length=8, unique=True, default=generate_affiliate_code)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.05)
    total_earnings = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_clicks = models.PositiveIntegerField(default=0)
    total_conversions = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'affiliate_profiles'
        verbose_name = 'Profil affilié'

    def __str__(self):
        return f'{self.user.email} - {self.code}'


class AffiliateLink(TimeStampedModel):
    affiliate = models.ForeignKey(AffiliateProfile, on_delete=models.CASCADE, related_name='links')
    product = models.ForeignKey('products.Product', on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey('categories.Category', on_delete=models.SET_NULL, null=True, blank=True)
    store = models.ForeignKey('vendors.Store', on_delete=models.SET_NULL, null=True, blank=True)
    custom_url = models.URLField(blank=True)
    code = models.CharField(max_length=20, unique=True, default=generate_affiliate_code)
    click_count = models.PositiveIntegerField(default=0)
    conversion_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'affiliate_links'
        verbose_name = 'Lien affilié'

    def __str__(self):
        return f'{self.affiliate.code} - {self.code}'


class AffiliateClick(models.Model):
    link = models.ForeignKey(AffiliateLink, on_delete=models.CASCADE, related_name='clicks')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'affiliate_clicks'
        verbose_name = 'Clic affilié'


class AffiliateConversion(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('paid', 'Payé'),
    ]

    link = models.ForeignKey(AffiliateLink, on_delete=models.CASCADE, related_name='conversions')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    class Meta:
        db_table = 'affiliate_conversions'
        verbose_name = 'Conversion affilié'

    def __str__(self):
        return f'{self.link.code} - {self.commission_amount}'


class AffiliatePayout(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processed', 'Traité'),
        ('rejected', 'Rejeté'),
    ]

    affiliate = models.ForeignKey(AffiliateProfile, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=30)
    account_number = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reference = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'affiliate_payouts'
        verbose_name = 'Paiement affilié'

    def __str__(self):
        return f'{self.affiliate.code} - {self.amount}'
