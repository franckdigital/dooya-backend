from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/featured/', views.FeaturedProductsView.as_view(), name='product-featured'),
    path('products/<slug:slug>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('vendor/products/', views.VendorProductListView.as_view(), name='vendor-product-list'),
    path('vendor/products/create/', views.VendorProductCreateView.as_view(), name='vendor-product-create'),
    path('vendor/products/<int:pk>/', views.VendorProductDetailView.as_view(), name='vendor-product-detail'),
    path('vendor/products/<int:pk>/images/', views.ProductImageView.as_view(), name='vendor-product-images'),
    path('vendor/products/<int:pk>/images/<int:image_id>/', views.ProductImageView.as_view(), name='vendor-product-image-delete'),
    path('vendor/products/<int:pk>/variants/', views.ProductVariantView.as_view(), name='vendor-product-variants'),
    path('vendor/products/<int:pk>/variants/<int:variant_id>/', views.ProductVariantView.as_view(), name='vendor-product-variant-detail'),
    path('vendor/products/import/', views.ProductImportView.as_view(), name='vendor-product-import'),
    path('vendor/products/<int:pk>/videos/', views.VendorProductVideoListView.as_view(), name='vendor-product-videos'),
    path('vendor/products/<int:pk>/videos/<int:video_id>/', views.VendorProductVideoDetailView.as_view(), name='vendor-product-video-detail'),
    path('admin/products/', views.AdminProductListView.as_view(), name='admin-product-list'),
    path('admin/products/<int:pk>/', views.AdminProductDetailView.as_view(), name='admin-product-detail'),
    path('admin/products/<int:pk>/images/', views.AdminProductImageView.as_view(), name='admin-product-images'),
    path('admin/products/<int:pk>/images/<int:image_id>/', views.AdminProductImageView.as_view(), name='admin-product-image-delete'),
    path('admin/tags/', views.AdminTagListCreateView.as_view(), name='admin-tag-list'),
    path('admin/tags/<int:pk>/', views.AdminTagDetailView.as_view(), name='admin-tag-detail'),
    path('admin/variants/', views.AdminVariantListView.as_view(), name='admin-variant-list'),
    path('admin/variants/<int:variant_id>/', views.AdminVariantDetailView.as_view(), name='admin-variant-detail'),
    path('admin/products/<int:pk>/variants/', views.AdminProductVariantView.as_view(), name='admin-product-variants'),
]
