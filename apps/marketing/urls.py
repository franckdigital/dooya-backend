from django.urls import path
from . import views

app_name = 'marketing'

urlpatterns = [
    # Campagnes (admin)
    path('admin/campaigns/', views.AdminCampaignListView.as_view(), name='campaign-list'),
    path('admin/campaigns/<int:pk>/', views.AdminCampaignDetailView.as_view(), name='campaign-detail'),
    path('admin/campaigns/<int:pk>/send/', views.AdminCampaignSendView.as_view(), name='campaign-send'),
    path('admin/campaigns/<int:pk>/duplicate/', views.AdminCampaignDuplicateView.as_view(), name='campaign-duplicate'),

    # Paniers abandonnés (admin)
    path('admin/abandoned-carts/', views.AdminAbandonedCartListView.as_view(), name='abandoned-carts'),
    path('admin/abandoned-carts/check/', views.AdminTriggerAbandonedCartCheck.as_view(), name='abandoned-carts-check'),

    # Désabonnement (utilisateur)
    path('unsubscribe/', views.UnsubscribeView.as_view(), name='unsubscribe'),
    path('resubscribe/<str:channel>/', views.ResubscribeView.as_view(), name='resubscribe'),
]
