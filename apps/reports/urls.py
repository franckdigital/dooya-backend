from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('reports/', views.ReportListView.as_view(), name='report-list'),
    path('reports/request/', views.ReportRequestView.as_view(), name='report-request'),
    path('reports/<int:pk>/download/', views.ReportDownloadView.as_view(), name='report-download'),
    path('admin/reports/', views.AdminReportView.as_view(), name='admin-report-list'),
]
