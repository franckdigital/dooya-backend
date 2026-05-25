from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.StockDashboardView.as_view(), name='dashboard'),

    # Entrepôts (admin)
    path('warehouses/', views.WarehouseListCreateView.as_view(), name='warehouse-list'),
    path('warehouses/<int:pk>/', views.WarehouseDetailView.as_view(), name='warehouse-detail'),

    # Emplacements stock
    path('locations/', views.StockLocationListView.as_view(), name='stock-location-list'),
    path('vendor/locations/', views.VendorStockLocationListView.as_view(), name='vendor-stock-locations'),

    # Mouvements
    path('movements/', views.StockMovementListView.as_view(), name='movement-list'),
    path('vendor/movements/', views.VendorStockMovementListView.as_view(), name='vendor-movements'),

    # Ajustements manuels
    path('adjust/', views.ManualStockAdjustmentView.as_view(), name='admin-adjust'),
    path('vendor/adjust/', views.VendorManualAdjustmentView.as_view(), name='vendor-adjust'),

    # Alertes
    path('alerts/', views.StockAlertListView.as_view(), name='alert-list'),
    path('alerts/<int:pk>/acknowledge/', views.StockAlertAcknowledgeView.as_view(), name='alert-acknowledge'),
    path('vendor/alerts/', views.VendorStockAlertListView.as_view(), name='vendor-alerts'),

    # Commandes fournisseurs
    path('supplier-orders/', views.SupplierOrderListCreateView.as_view(), name='supplier-order-list'),
    path('supplier-orders/<int:pk>/', views.SupplierOrderDetailView.as_view(), name='supplier-order-detail'),
    path('supplier-orders/<int:pk>/receive/', views.SupplierOrderReceiveView.as_view(), name='supplier-order-receive'),
]
