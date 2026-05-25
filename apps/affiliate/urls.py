from django.urls import path
from . import views

app_name = 'affiliate'

urlpatterns = [
    path('affiliate/profile/', views.AffiliateProfileView.as_view(), name='affiliate-profile'),
    path('affiliate/links/', views.AffiliateLinkListCreateView.as_view(), name='affiliate-link-list'),
    path('affiliate/links/<int:link_id>/', views.AffiliateLinkListCreateView.as_view(), name='affiliate-link-delete'),
    path('affiliate/click/<str:code>/', views.AffiliateLinkClickView.as_view(), name='affiliate-click'),
    path('affiliate/stats/', views.AffiliateStatsView.as_view(), name='affiliate-stats'),
    path('affiliate/conversions/', views.AffiliateConversionListView.as_view(), name='affiliate-conversions'),
    path('affiliate/payout/', views.AffiliatePayoutRequestView.as_view(), name='affiliate-payout'),
    path('admin/affiliates/', views.AdminAffiliateListView.as_view(), name='admin-affiliate-list'),
    path('admin/affiliate-payouts/', views.AdminAffiliatePayoutView.as_view(), name='admin-affiliate-payouts'),
    path('admin/affiliate-payouts/<int:pk>/', views.AdminAffiliatePayoutView.as_view(), name='admin-affiliate-payout-action'),
]
