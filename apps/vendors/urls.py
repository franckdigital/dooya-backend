from django.urls import path
from . import views

app_name = 'vendors'

urlpatterns = [
    path('stores/', views.StoreListView.as_view(), name='store-list'),
    path('stores/<slug:slug>/', views.StoreDetailView.as_view(), name='store-detail'),
    path('vendor/store/', views.VendorStoreView.as_view(), name='vendor-store'),
    path('vendor/dashboard/', views.VendorDashboardView.as_view(), name='vendor-dashboard'),
    path('vendor/documents/', views.StoreDocumentView.as_view(), name='vendor-documents'),
    path('vendor/bank-account/', views.BankAccountView.as_view(), name='vendor-bank-account'),
    path('admin/stores/', views.AdminStoreListView.as_view(), name='admin-store-list'),
    path('admin/stores/<int:pk>/action/', views.AdminStoreActionView.as_view(), name='admin-store-action'),
]
