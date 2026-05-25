from django.db import models
from django.conf import settings
from core.models import TimeStampedModel


class Page(TimeStampedModel):
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=320, unique=True)
    content = models.TextField()
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = 'pages'
        verbose_name = 'Page'

    def __str__(self):
        return self.title


class Slider(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=400, blank=True)
    image = models.ImageField(upload_to='cms/sliders/')
    button_text = models.CharField(max_length=100, blank=True)
    button_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    badge         = models.CharField(max_length=100, blank=True)
    tag           = models.CharField(max_length=100, blank=True)
    price         = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    compare_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    bg_gradient   = models.CharField(max_length=200, blank=True, default='from-[#F7941D] via-[#f9a84d] to-[#fbbf24]')
    accent_color  = models.CharField(max_length=20, blank=True, default='#1C3525')
    emoji         = models.CharField(max_length=10, blank=True)

    class Meta:
        db_table = 'sliders'
        verbose_name = 'Slider'
        ordering = ['order']

    def __str__(self):
        return self.title


class Banner(TimeStampedModel):
    POSITION_CHOICES = [
        ('hero', 'Hero'),
        ('sidebar', 'Barre latérale'),
        ('footer', 'Pied de page'),
        ('popup', 'Popup'),
    ]

    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='cms/banners/')
    link = models.URLField(blank=True)
    position = models.CharField(max_length=20, choices=POSITION_CHOICES)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    click_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'banners'
        verbose_name = 'Bannière'

    def __str__(self):
        return f'{self.title} ({self.position})'


class SidebarCard(models.Model):
    CARD_TYPE_CHOICES = [
        ('info',  'Info'),
        ('promo', 'Promo'),
    ]
    icon       = models.CharField(max_length=10, blank=True)
    title      = models.CharField(max_length=200)
    subtitle   = models.CharField(max_length=300, blank=True)
    link       = models.CharField(max_length=500, blank=True)
    card_type  = models.CharField(max_length=10, choices=CARD_TYPE_CHOICES, default='info')
    bg_color   = models.CharField(max_length=100, blank=True)
    order      = models.PositiveIntegerField(default=0)
    is_active  = models.BooleanField(default=True)

    class Meta:
        db_table = 'sidebar_cards'
        verbose_name = 'Carte latérale'
        ordering = ['order']

    def __str__(self):
        return self.title


class BlogCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=110, unique=True)

    class Meta:
        db_table = 'blog_categories'
        verbose_name = 'Catégorie blog'

    def __str__(self):
        return self.name


class BlogPost(TimeStampedModel):
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=320, unique=True)
    content = models.TextField()
    excerpt = models.TextField(blank=True)
    image = models.ImageField(upload_to='blog/', blank=True, null=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='blog_posts')
    category = models.ForeignKey(BlogCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    tags = models.ManyToManyField('products.Tag', blank=True, related_name='blog_posts')
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    views_count = models.PositiveIntegerField(default=0)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)

    class Meta:
        db_table = 'blog_posts'
        verbose_name = 'Article blog'
        ordering = ['-published_at']

    def __str__(self):
        return self.title


class Coupon(models.Model):
    TYPE_CHOICES = [
        ('percentage', 'Pourcentage'),
        ('fixed', 'Montant fixe'),
    ]

    code = models.CharField(max_length=50, unique=True)
    type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    applicable_categories = models.ManyToManyField('categories.Category', blank=True, related_name='coupons')

    class Meta:
        db_table = 'coupons'
        verbose_name = 'Coupon'

    def __str__(self):
        return f'{self.code} ({self.type}: {self.value})'

    @property
    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False
        return True
