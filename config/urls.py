from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

API_V1 = 'api/v1/'

urlpatterns = [
    path('admin/', admin.site.urls),

    # Documentation API
    path(f'{API_V1}schema/', SpectacularAPIView.as_view(), name='schema'),
    path(f'{API_V1}docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path(f'{API_V1}redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Modules
    path(f'{API_V1}auth/', include('apps.authentication.urls')),
    path(f'{API_V1}users/', include('apps.users.urls')),
    path(f'{API_V1}vendors/', include('apps.vendors.urls')),
    path(f'{API_V1}categories/', include('apps.categories.urls')),
    path(f'{API_V1}products/', include('apps.products.urls')),
    path(f'{API_V1}cart/', include('apps.cart.urls')),
    path(f'{API_V1}orders/', include('apps.orders.urls')),
    path(f'{API_V1}payments/', include('apps.payments.urls')),
    path(f'{API_V1}deliveries/', include('apps.deliveries.urls')),
    path(f'{API_V1}reviews/', include('apps.reviews.urls')),
    path(f'{API_V1}notifications/', include('apps.notifications.urls')),
    path(f'{API_V1}analytics/', include('apps.analytics.urls')),
    path(f'{API_V1}affiliate/', include('apps.affiliate.urls')),
    path(f'{API_V1}wallets/', include('apps.wallets.urls')),
    path(f'{API_V1}chat/', include('apps.chat.urls')),
    path(f'{API_V1}cms/', include('apps.cms.urls')),
    path(f'{API_V1}reports/', include('apps.reports.urls')),
    path(f'{API_V1}sav/', include('apps.sav.urls')),
    path(f'{API_V1}support/', include('apps.support.urls')),
    path(f'{API_V1}inventory/', include('apps.inventory.urls')),
    path(f'{API_V1}suppliers/', include('apps.suppliers.urls')),
    path(f'{API_V1}quality/', include('apps.quality.urls')),
    path(f'{API_V1}audit/', include('apps.audit.urls')),
    path(f'{API_V1}live/', include('apps.live.urls')),
    path(f'{API_V1}recommendations/', include('apps.recommendations.urls')),
    path(f'{API_V1}search/', include('apps.search.urls')),
    path(f'{API_V1}marketing/', include('apps.marketing.urls')),
    path(f'{API_V1}commissions/', include('apps.commissions.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
