from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('admin/analytics/dashboard/', views.AdminDashboardView.as_view(), name='admin-dashboard'),
    path('admin/analytics/sales-chart/', views.AdminSalesChartView.as_view(), name='admin-sales-chart'),
    path('admin/analytics/top-products/', views.AdminTopProductsView.as_view(), name='admin-top-products'),
    path('admin/analytics/top-vendors/', views.AdminTopVendorsView.as_view(), name='admin-top-vendors'),
    path('admin/analytics/users/', views.AdminUserStatsView.as_view(), name='admin-user-stats'),
    path('vendor/analytics/', views.VendorAnalyticsView.as_view(), name='vendor-analytics'),
]
