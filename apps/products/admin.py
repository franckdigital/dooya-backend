from django.contrib import admin
from .models import Product, ProductImage, ProductVariant, Tag, ProductView


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    readonly_fields = ['is_primary', 'order']


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'store', 'category', 'price', 'stock', 'rating', 'is_active', 'is_featured', 'created_at']
    list_filter = ['is_active', 'is_featured', 'is_digital', 'category', 'store']
    search_fields = ['name', 'sku', 'store__name']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['views_count', 'rating', 'reviews_count', 'created_at', 'updated_at']
    filter_horizontal = ['tags']
    inlines = [ProductImageInline, ProductVariantInline]
    list_editable = ['is_active', 'is_featured']


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'is_primary', 'order']
    list_filter = ['is_primary']
    search_fields = ['product__name']


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'name', 'sku', 'price', 'stock']
    search_fields = ['product__name', 'name', 'sku']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(ProductView)
class ProductViewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'ip_address', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['product', 'user', 'session_key', 'ip_address', 'created_at']
