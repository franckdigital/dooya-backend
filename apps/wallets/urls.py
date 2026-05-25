from django.urls import path
from . import views

app_name = 'wallets'

urlpatterns = [
    path('wallet/', views.WalletView.as_view(), name='wallet'),
    path('wallet/transactions/', views.WalletTransactionListView.as_view(), name='wallet-transactions'),
    path('wallet/withdraw/', views.WithdrawalRequestView.as_view(), name='withdrawal-request'),
    path('admin/withdrawals/', views.AdminWithdrawalListView.as_view(), name='admin-withdrawal-list'),
    path('admin/withdrawals/<int:pk>/', views.AdminWithdrawalActionView.as_view(), name='admin-withdrawal-action'),
]
