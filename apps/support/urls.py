from django.urls import path
from . import views

app_name = 'support'

urlpatterns = [
    # FAQ publique
    path('faq/categories/', views.FAQCategoryListView.as_view(), name='faq-categories'),
    path('faq/', views.FAQListView.as_view(), name='faq-list'),
    path('faq/<int:pk>/', views.FAQDetailView.as_view(), name='faq-detail'),

    # Tickets support
    path('tickets/', views.MySupportTicketListCreateView.as_view(), name='my-ticket-list'),
    path('tickets/<int:pk>/', views.MySupportTicketDetailView.as_view(), name='my-ticket-detail'),
    path('tickets/<int:pk>/messages/', views.TicketMessageCreateView.as_view(), name='ticket-message'),
    path('tickets/<int:pk>/rate/', views.TicketRateView.as_view(), name='ticket-rate'),

    # Contentieux
    path('disputes/', views.MyDisputeListCreateView.as_view(), name='my-dispute-list'),
    path('disputes/<int:pk>/', views.MyDisputeDetailView.as_view(), name='my-dispute-detail'),
    path('disputes/<int:pk>/evidences/', views.DisputeEvidenceCreateView.as_view(), name='dispute-evidence'),
    path('disputes/<int:pk>/messages/', views.DisputeMessageCreateView.as_view(), name='dispute-message'),

    # Admin
    path('admin/faq/', views.AdminFAQListCreateView.as_view(), name='admin-faq-list'),
    path('admin/faq/<int:pk>/', views.AdminFAQDetailView.as_view(), name='admin-faq-detail'),
    path('admin/tickets/', views.AdminTicketListView.as_view(), name='admin-ticket-list'),
    path('admin/tickets/<int:pk>/', views.AdminTicketDetailView.as_view(), name='admin-ticket-detail'),
    path('admin/disputes/', views.AdminDisputeListView.as_view(), name='admin-dispute-list'),
    path('admin/disputes/<int:pk>/', views.AdminDisputeDetailView.as_view(), name='admin-dispute-detail'),
    path('admin/disputes/<int:pk>/decision/', views.AdminDisputeDecisionView.as_view(), name='admin-dispute-decision'),
]
