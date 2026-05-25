from django.contrib import admin
from mptt.admin import DraggableMPTTAdmin
from .models import Category, Attribute, AttributeValue


class AttributeValueInline(admin.TabularInline):
    model = AttributeValue
    extra = 1
    fields = ['value', 'color_hex', 'order']


@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    list_display = ['tree_actions', 'indented_title', 'slug', 'is_active', 'order']
    list_display_links = ['indented_title']
    list_filter = ['is_active']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'is_filterable', 'is_required', 'order']
    list_filter = ['type', 'is_filterable']
    search_fields = ['name']
    filter_horizontal = ['categories']
    inlines = [AttributeValueInline]
    prepopulated_fields = {'slug': ('name',)}


@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    list_display = ['attribute', 'value', 'color_hex', 'order']
    list_filter = ['attribute']
    search_fields = ['value', 'attribute__name']
