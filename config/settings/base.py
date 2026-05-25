from pathlib import Path
from decouple import config
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    'django_filters',
    'mptt',
    'axes',
    'channels',
    'social_django',
    'django_celery_beat',
    'django_celery_results',
    'imagekit',
    'phonenumber_field',
]

LOCAL_APPS = [
    'core',
    'apps.authentication',
    'apps.users',
    'apps.vendors',
    'apps.categories',
    'apps.products',
    'apps.cart',
    'apps.orders',
    'apps.payments',
    'apps.deliveries',
    'apps.reviews',
    'apps.notifications',
    'apps.analytics',
    'apps.affiliate',
    'apps.wallets',
    'apps.chat',
    'apps.cms',
    'apps.reports',
    'apps.sav',
    'apps.support',
    'apps.inventory',
    'apps.suppliers',
    'apps.quality',
    'apps.audit',
    'apps.live',
    'apps.recommendations',
    'apps.search',
    'apps.marketing',
    'apps.commissions',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'axes.middleware.AxesMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

AUTH_USER_MODEL = 'users.User'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='dooya_db'),
        'USER': config('DB_USER', default='root'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Abidjan'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── REST Framework ────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'auth': '10/minute',
    },
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
}

# ─── SimpleJWT ─────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ─── API Documentation ─────────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    'TITLE': 'Dooya Marketplace API',
    'DESCRIPTION': 'API REST complète pour la plateforme e-commerce Dooya',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'TAGS': [
        {'name': 'auth', 'description': 'Authentification'},
        {'name': 'users', 'description': 'Gestion utilisateurs'},
        {'name': 'vendors', 'description': 'Gestion vendeurs'},
        {'name': 'products', 'description': 'Catalogue produits'},
        {'name': 'categories', 'description': 'Catégories'},
        {'name': 'cart', 'description': 'Panier'},
        {'name': 'orders', 'description': 'Commandes'},
        {'name': 'payments', 'description': 'Paiements'},
        {'name': 'deliveries', 'description': 'Livraisons'},
        {'name': 'reviews', 'description': 'Avis'},
        {'name': 'notifications', 'description': 'Notifications'},
        {'name': 'analytics', 'description': 'Analytiques'},
        {'name': 'affiliate', 'description': 'Affiliation'},
        {'name': 'wallets', 'description': 'Portefeuilles'},
        {'name': 'chat', 'description': 'Messagerie'},
        {'name': 'cms', 'description': 'Gestion de contenu'},
        {'name': 'reports', 'description': 'Rapports'},
        {'name': 'sav', 'description': 'Service Après-Vente'},
        {'name': 'support', 'description': 'Support & Contentieux'},
        {'name': 'inventory', 'description': 'Gestion du Stock'},
        {'name': 'suppliers', 'description': 'Fournisseurs'},
        {'name': 'quality', 'description': 'Qualité & Retours'},
        {'name': 'Audit', 'description': 'Audit & Business Intelligence'},
        {'name': 'Live Shopping', 'description': 'Sessions live, achat instantané'},
        {'name': 'Recommandations', 'description': 'IA Recommandations produits'},
        {'name': 'Recherche', 'description': 'Recherche intelligente & vocale'},
        {'name': 'Marketing', 'description': 'Campagnes marketing & relances paniers'},
        {'name': 'Commissions', 'description': 'Commissions marketplace & reversements vendeurs'},
    ],
}

# ─── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173,http://127.0.0.1:5173',
    cast=lambda v: [s.strip() for s in v.split(',')]
)
CORS_ALLOW_CREDENTIALS = True

# ─── Redis & Cache ─────────────────────────────────────────────────────────────
REDIS_URL = config('REDIS_URL', default='redis://127.0.0.1:6379')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'{REDIS_URL}/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'TIMEOUT': 300,
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# ─── Celery ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = f'{REDIS_URL}/0'
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'default'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BEAT_SCHEDULE = {
    'release-expired-reservations': {
        'task': 'inventory.release_expired_reservations',
        'schedule': 300,  # toutes les 5 minutes
    },
    'check-low-stock': {
        'task': 'inventory.check_low_stock',
        'schedule': 3600,  # toutes les heures
    },
    'auto-create-supplier-orders': {
        'task': 'inventory.auto_create_supplier_orders',
        'schedule': 86400,  # chaque nuit
    },
    'audit-monthly-snapshots': {
        'task': 'audit.compute_monthly_snapshots',
        'schedule': 86400,  # vérification quotidienne, effectif le 1er du mois
    },
    'marketing-schedule-due-campaigns': {
        'task': 'marketing.schedule_due_campaigns',
        'schedule': 300,  # toutes les 5 minutes
    },
    'marketing-check-abandoned-carts': {
        'task': 'marketing.check_abandoned_carts',
        'schedule': 3600,  # toutes les heures
    },
}

# ─── Django Channels ───────────────────────────────────────────────────────────
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {'hosts': [f'{REDIS_URL}/2']},
    }
}

# ─── Social Auth ───────────────────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.facebook.FacebookOAuth2',
    'django.contrib.auth.backends.ModelBackend',
]

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = config('GOOGLE_CLIENT_ID', default='')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = config('GOOGLE_CLIENT_SECRET', default='')
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ['email', 'profile']

SOCIAL_AUTH_FACEBOOK_KEY = config('FACEBOOK_APP_ID', default='')
SOCIAL_AUTH_FACEBOOK_SECRET = config('FACEBOOK_APP_SECRET', default='')
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email', 'public_profile']

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'apps.authentication.pipeline.save_profile',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

# ─── Django Axes (brute force protection) ─────────────────────────────────────
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=30)
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_CALLABLE = 'core.utils.axes_lockout_response'

# ─── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Dooya <noreply@dooya.com>')

# ─── SMS / WhatsApp ────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER', default='')
WHATSAPP_PHONE_NUMBER = config('WHATSAPP_PHONE_NUMBER', default='')
WHATSAPP_API_URL = config('WHATSAPP_API_URL', default='https://graph.facebook.com/v18.0')
WHATSAPP_ACCESS_TOKEN = config('WHATSAPP_ACCESS_TOKEN', default='')

AFRICASTALKING_USERNAME = config('AFRICASTALKING_USERNAME', default='')
AFRICASTALKING_API_KEY = config('AFRICASTALKING_API_KEY', default='')

# ─── Firebase (Push Notifications) ────────────────────────────────────────────
FIREBASE_CREDENTIALS_PATH = config('FIREBASE_CREDENTIALS_PATH', default='')
FCM_SERVER_KEY = config('FCM_SERVER_KEY', default='')

# ─── Payments ──────────────────────────────────────────────────────────────────
CINETPAY_API_KEY = config('CINETPAY_API_KEY', default='')
CINETPAY_SITE_ID = config('CINETPAY_SITE_ID', default='')
CINETPAY_BASE_URL = 'https://api-checkout.cinetpay.com/v2'

PAYDUNYA_MASTER_KEY = config('PAYDUNYA_MASTER_KEY', default='')
PAYDUNYA_PRIVATE_KEY = config('PAYDUNYA_PRIVATE_KEY', default='')
PAYDUNYA_TOKEN = config('PAYDUNYA_TOKEN', default='')
PAYDUNYA_BASE_URL = 'https://app.paydunya.com/api/v1'

FLUTTERWAVE_PUBLIC_KEY = config('FLUTTERWAVE_PUBLIC_KEY', default='')
FLUTTERWAVE_SECRET_KEY = config('FLUTTERWAVE_SECRET_KEY', default='')
FLUTTERWAVE_BASE_URL = 'https://api.flutterwave.com/v3'

# ─── Storage ───────────────────────────────────────────────────────────────────
USE_S3 = config('USE_S3', default=False, cast=bool)
if USE_S3:
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_DEFAULT_ACL = 'public-read'
    AWS_S3_FILE_OVERWRITE = False
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# ─── PhoneNumber ───────────────────────────────────────────────────────────────
PHONENUMBER_DEFAULT_REGION = 'CI'

# ─── Marketplace Config ────────────────────────────────────────────────────────
MARKETPLACE_COMMISSION_RATE = config('COMMISSION_RATE', default=0.10, cast=float)
MARKETPLACE_MIN_WITHDRAWAL = config('MIN_WITHDRAWAL', default=5000, cast=int)
SITE_NAME = 'Dooya'
SITE_URL = config('SITE_URL', default='http://localhost:5173')
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:5173')
