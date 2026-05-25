from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Address, Favorite, OTPCode


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'full_name', 'role', 'is_active', 'is_phone_verified', 'date_joined']
    list_filter = ['role', 'is_active', 'is_phone_verified', 'is_email_verified']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-date_joined']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Dooya', {'fields': ('phone', 'role', 'avatar', 'is_phone_verified', 'is_email_verified', 'fcm_token')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Dooya', {'fields': ('email', 'phone', 'role')}),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'label', 'full_name', 'city', 'country', 'is_default']
    list_filter = ['label', 'country', 'is_default']
    search_fields = ['user__email', 'full_name', 'city']


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    search_fields = ['user__email', 'product__name']


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'purpose', 'is_used', 'expires_at']
    list_filter = ['purpose', 'is_used']
