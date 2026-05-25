from django.db import models
from mptt.models import MPTTModel, TreeForeignKey


class Category(MPTTModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    parent = TreeForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children'
    )
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    icon = models.CharField(max_length=100, blank=True, help_text='Nom d\'icône (ex: shopping-bag)')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)

    class MPTTMeta:
        order_insertion_by = ['order', 'name']

    class Meta:
        db_table = 'categories'
        verbose_name = 'Catégorie'
        verbose_name_plural = 'Catégories'

    def __str__(self):
        return self.name

    @property
    def full_path(self):
        ancestors = self.get_ancestors(include_self=True)
        return ' > '.join(a.name for a in ancestors)

    @property
    def is_leaf(self):
        return not self.children.filter(is_active=True).exists()

    @property
    def products_count(self):
        ids = self.get_descendants(include_self=True).values_list('id', flat=True)
        from apps.products.models import Product
        return Product.objects.filter(category_id__in=ids, is_active=True).count()


class Attribute(models.Model):
    TYPE_CHOICES = [
        ('select', 'Liste de choix'),
        ('multiselect', 'Choix multiples'),
        ('text', 'Texte libre'),
        ('number', 'Nombre'),
        ('boolean', 'Oui/Non'),
        ('color', 'Couleur'),
    ]
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='select')
    unit = models.CharField(max_length=30, blank=True, help_text='Ex: cm, kg, L')
    is_filterable = models.BooleanField(default=True, help_text='Afficher dans les filtres')
    is_required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    categories = models.ManyToManyField(Category, blank=True, related_name='attributes')

    class Meta:
        db_table = 'attributes'
        verbose_name = 'Attribut'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class AttributeValue(models.Model):
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name='values')
    value = models.CharField(max_length=200)
    color_hex = models.CharField(max_length=7, blank=True, help_text='Ex: #FF0000 pour les attributs couleur')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'attribute_values'
        verbose_name = 'Valeur attribut'
        ordering = ['order', 'value']
        unique_together = ('attribute', 'value')

    def __str__(self):
        return f'{self.attribute.name}: {self.value}'
