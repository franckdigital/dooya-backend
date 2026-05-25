from django.urls import path
from . import views

app_name = 'quality'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.QualityDashboardView.as_view(), name='dashboard'),

    # Profils qualité produit
    path('products/<int:product_pk>/profile/', views.ProductQualityProfileView.as_view(), name='product-quality-profile'),
    path('admin/profiles/', views.AdminProductQualityListView.as_view(), name='admin-quality-profiles'),
    path('vendor/profiles/', views.VendorProductQualityListView.as_view(), name='vendor-quality-profiles'),

    # Inspections
    path('inspections/', views.QualityInspectionListCreateView.as_view(), name='inspection-list'),
    path('inspections/<int:pk>/', views.QualityInspectionDetailView.as_view(), name='inspection-detail'),
    path('vendor/inspections/', views.VendorQualityInspectionListView.as_view(), name='vendor-inspections'),

    # Retours produits (client)
    path('returns/', views.MyProductReturnListCreateView.as_view(), name='my-return-list'),
    path('returns/<int:pk>/', views.MyProductReturnDetailView.as_view(), name='my-return-detail'),
    path('returns/<int:pk>/images/', views.ProductReturnAddImageView.as_view(), name='return-add-images'),

    # Retours (admin)
    path('admin/returns/', views.AdminProductReturnListView.as_view(), name='admin-return-list'),
    path('admin/returns/<int:pk>/', views.AdminProductReturnDetailView.as_view(), name='admin-return-detail'),
    path('admin/returns/<int:pk>/process/', views.AdminProductReturnProcessView.as_view(), name='admin-return-process'),
    path('admin/returns/<int:pk>/advance/', views.AdminProductReturnAdvanceView.as_view(), name='admin-return-advance'),

    # Retours (vendeur)
    path('vendor/returns/', views.VendorProductReturnListView.as_view(), name='vendor-return-list'),

    # Avis non-conformité fournisseur
    path('notices/', views.SupplierQualityNoticeListCreateView.as_view(), name='notice-list'),
    path('notices/<int:pk>/', views.SupplierQualityNoticeDetailView.as_view(), name='notice-detail'),
    path('notices/<int:pk>/send/', views.SupplierQualityNoticeSendView.as_view(), name='notice-send'),
]
