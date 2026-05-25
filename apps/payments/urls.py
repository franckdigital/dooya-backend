from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('payments/initiate/', views.PaymentInitiateView.as_view(), name='payment-initiate'),
    path('payments/callback/', views.PaymentCallbackView.as_view(), name='payment-callback'),
    path('payments/webhook/<str:gateway_name>/', views.PaymentWebhookView.as_view(), name='payment-webhook'),
    path('payments/<str:reference>/status/', views.PaymentStatusView.as_view(), name='payment-status'),
    path('payments/refund/', views.RefundRequestView.as_view(), name='refund-request'),

    # Installment — client
    path('payments/installment/contract/', views.InstallmentContractView.as_view(), name='installment-contract'),
    path('payments/installment/', views.InstallmentPlanView.as_view(), name='installment-plan'),
    path('payments/installment/<int:plan_id>/sign/', views.InstallmentSignContractView.as_view(), name='installment-sign'),
    path('payments/installment/pay/<int:installment_id>/', views.InstallmentPayView.as_view(), name='installment-pay'),

    # Admin
    path('admin/payments/', views.AdminPaymentListView.as_view(), name='admin-payment-list'),
    path('admin/refunds/', views.AdminRefundView.as_view(), name='admin-refund-list'),
    path('admin/refunds/<int:refund_id>/', views.AdminRefundView.as_view(), name='admin-refund-action'),
    path('admin/installments/', views.AdminInstallmentPlanListView.as_view(), name='admin-installment-list'),
    path('admin/installments/<int:pk>/', views.AdminInstallmentPlanDetailView.as_view(), name='admin-installment-detail'),
    path('admin/installments/verify/<int:installment_id>/', views.AdminInstallmentVerifyView.as_view(), name='admin-installment-verify'),
]
