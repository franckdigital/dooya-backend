from django.contrib import admin
from .models import Wallet, WalletTransaction, WithdrawalRequest


class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction
    extra = 0
    readonly_fields = ['type', 'amount', 'balance_before', 'balance_after', 'reference', 'description', 'created_at']
    max_num = 20


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance', 'currency', 'is_active', 'updated_at']
    list_filter = ['currency', 'is_active']
    search_fields = ['user__email']
    readonly_fields = ['balance', 'updated_at', 'created_at']
    inlines = [WalletTransactionInline]


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['wallet', 'type', 'amount', 'balance_after', 'category', 'created_at']
    list_filter = ['type', 'category']
    search_fields = ['reference', 'wallet__user__email']
    readonly_fields = ['reference', 'created_at']


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ['wallet', 'amount', 'method', 'status', 'processed_at', 'created_at']
    list_filter = ['status', 'method']
    search_fields = ['wallet__user__email', 'account_name']
