from django.db import models
from django.conf import settings


class SiteVisit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    page = models.CharField(max_length=500)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referrer = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'site_visits'
        verbose_name = 'Visite site'


class SearchQuery(models.Model):
    query = models.CharField(max_length=300)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    results_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'search_queries'
        verbose_name = 'Requête de recherche'

    def __str__(self):
        return self.query


class SalesStat(models.Model):
    date = models.DateField(unique=True)
    orders_count = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    new_users = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'sales_stats'
        verbose_name = 'Statistique ventes'
        ordering = ['-date']

    def __str__(self):
        return f'{self.date}: {self.orders_count} commandes, {self.revenue} XOF'
