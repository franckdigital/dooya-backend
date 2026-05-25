from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    # Metrics
    path('metrics/sales/', views.SalesMetricsView.as_view(), name='metrics-sales'),
    path('metrics/customers/', views.CustomerMetricsView.as_view(), name='metrics-customers'),
    path('metrics/products/', views.ProductMetricsView.as_view(), name='metrics-products'),
    path('metrics/vendors/', views.VendorMetricsView.as_view(), name='metrics-vendors'),
    path('metrics/quality/', views.QualityMetricsView.as_view(), name='metrics-quality'),
    path('metrics/delivery/', views.DeliveryMetricsView.as_view(), name='metrics-delivery'),
    path('metrics/support/', views.SupportMetricsView.as_view(), name='metrics-support'),
    path('metrics/full/', views.FullMetricsView.as_view(), name='metrics-full'),

    # Snapshots
    path('snapshots/', views.SnapshotListView.as_view(), name='snapshot-list'),
    path('snapshots/<int:pk>/', views.SnapshotDetailView.as_view(), name='snapshot-detail'),
    path('snapshots/compute/', views.ComputeSnapshotView.as_view(), name='snapshot-compute'),

    # KPI Alerts
    path('alerts/', views.KPIAlertListView.as_view(), name='alert-list'),
    path('alerts/<int:pk>/acknowledge/', views.KPIAlertAcknowledgeView.as_view(), name='alert-acknowledge'),
    path('alerts/acknowledge-all/', views.KPIAlertBulkAcknowledgeView.as_view(), name='alert-acknowledge-all'),

    # Reports
    path('reports/', views.AuditReportListView.as_view(), name='report-list'),
    path('reports/<int:pk>/', views.AuditReportDetailView.as_view(), name='report-detail'),
    path('reports/generate/', views.GenerateReportView.as_view(), name='report-generate'),
]
