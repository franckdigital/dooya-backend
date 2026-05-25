from django.contrib import admin
from .models import Store, StoreDocument, BankAccount


class StoreDocumentInline(admin.TabularInline):
    model = StoreDocument
    extra = 0
    readonly_fields = ['is_verified', 'created_at']


class BankAccountInline(admin.StackedInline):
    model = BankAccount
    extra = 0
    readonly_fields = ['is_verified']


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'city', 'status', 'is_certified', 'is_featured', 'rating', 'total_sales', 'created_at']
    list_filter = ['status', 'is_certified', 'is_featured', 'country']
    search_fields = ['name', 'user__email', 'city']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['total_sales', 'total_revenue', 'rating', 'created_at', 'updated_at']
    inlines = [StoreDocumentInline, BankAccountInline]
    actions = ['approve_stores', 'suspend_stores']

    def approve_stores(self, request, queryset):
        queryset.update(status='active')
    approve_stores.short_description = 'Approuver les boutiques sélectionnées'

    def suspend_stores(self, request, queryset):
        queryset.update(status='suspended')
    suspend_stores.short_description = 'Suspendre les boutiques sélectionnées'


@admin.register(StoreDocument)
class StoreDocumentAdmin(admin.ModelAdmin):
    list_display = ['store', 'document_type', 'is_verified', 'created_at']
    list_filter = ['document_type', 'is_verified']
    search_fields = ['store__name']


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['store', 'bank_name', 'account_name', 'is_verified']
    list_filter = ['is_verified', 'bank_name']
    search_fields = ['store__name', 'account_name']
