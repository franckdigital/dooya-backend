from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('orders/', views.OrderListView.as_view(), name='order-list'),
    path('orders/create/', views.OrderCreateView.as_view(), name='order-create'),
    path('orders/<str:order_number>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('orders/<str:order_number>/cancel/', views.OrderCancelView.as_view(), name='order-cancel'),
    path('orders/<str:order_number>/invoice/', views.InvoiceDownloadView.as_view(), name='order-invoice'),
    path('vendor/orders/', views.VendorOrderListView.as_view(), name='vendor-order-list'),
    path('vendor/orders/<str:order_number>/', views.VendorOrderDetailView.as_view(), name='vendor-order-detail'),
    path('vendor/orders/<str:order_number>/status/', views.VendorOrderUpdateStatusView.as_view(), name='vendor-order-status'),
    path('admin/orders/', views.AdminOrderListView.as_view(), name='admin-order-list'),
    path('admin/orders/<str:order_number>/', views.AdminOrderDetailView.as_view(), name='admin-order-detail'),
    path('admin/orders/<str:order_number>/status/', views.AdminOrderUpdateStatusView.as_view(), name='admin-order-status'),
]
