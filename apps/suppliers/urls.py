from django.urls import path
from . import views

app_name = 'suppliers'

urlpatterns = [
    # Dashboard admin
    path('dashboard/', views.SupplierDashboardView.as_view(), name='dashboard'),

    # Fournisseurs
    path('', views.AdminSupplierListCreateView.as_view(), name='supplier-list'),
    path('<int:pk>/', views.AdminSupplierDetailView.as_view(), name='supplier-detail'),
    path('<int:pk>/approve/', views.AdminSupplierApproveView.as_view(), name='supplier-approve'),
    path('vendor/', views.VendorSupplierListView.as_view(), name='vendor-supplier-list'),

    # Produits fournisseurs
    path('products/', views.SupplierProductListCreateView.as_view(), name='supplier-product-list'),
    path('products/<int:pk>/', views.SupplierProductDetailView.as_view(), name='supplier-product-detail'),
    path('products/by-product/<int:product_pk>/', views.ProductSuppliersView.as_view(), name='product-suppliers'),

    # Contrats
    path('contracts/', views.SupplierContractListCreateView.as_view(), name='contract-list'),
    path('contracts/<int:pk>/', views.SupplierContractDetailView.as_view(), name='contract-detail'),

    # Performance
    path('performance/', views.SupplierPerformanceListView.as_view(), name='performance-list'),
]
