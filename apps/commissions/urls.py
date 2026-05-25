from django.urls import path
from . import views

app_name = 'commissions'

urlpatterns = [
    # Admin — Règles
    path('admin/rules/', views.AdminCommissionRuleListView.as_view(), name='admin-rule-list'),
    path('admin/rules/<int:pk>/', views.AdminCommissionRuleDetailView.as_view(), name='admin-rule-detail'),

    # Admin — Commissions
    path('admin/commissions/', views.AdminCommissionListView.as_view(), name='admin-commission-list'),
    path('admin/commissions/summary/', views.AdminCommissionSummaryView.as_view(), name='admin-commission-summary'),

    # Admin — Reversements
    path('admin/payouts/', views.AdminPayoutListView.as_view(), name='admin-payout-list'),
    path('admin/payouts/create/', views.AdminCreatePayoutView.as_view(), name='admin-payout-create'),
    path('admin/payouts/<int:pk>/', views.AdminPayoutDetailView.as_view(), name='admin-payout-detail'),
    path('admin/payouts/<int:pk>/mark-paid/', views.AdminMarkPayoutPaidView.as_view(), name='admin-payout-paid'),

    # Vendeur
    path('vendor/commissions/', views.VendorCommissionListView.as_view(), name='vendor-commission-list'),
    path('vendor/commissions/summary/', views.VendorCommissionSummaryView.as_view(), name='vendor-commission-summary'),
    path('vendor/payouts/', views.VendorPayoutListView.as_view(), name='vendor-payout-list'),
]
