from django.urls import path
from . import views

urlpatterns = [
    path('me/', views.MeView.as_view(), name='me'),
    path('me/change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('me/addresses/', views.AddressListCreateView.as_view(), name='address-list'),
    path('me/addresses/<int:pk>/', views.AddressDetailView.as_view(), name='address-detail'),
    path('me/favorites/', views.FavoriteListView.as_view(), name='favorites'),
    path('me/favorites/<int:product_id>/', views.FavoriteToggleView.as_view(), name='favorite-toggle'),
    path('', views.UserListView.as_view(), name='user-list'),
    path('<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    # Admin commercial management
    path('commercials/', views.AdminCommercialListCreateView.as_view(), name='commercial-list'),
    path('commercials/<int:pk>/', views.AdminCommercialDetailView.as_view(), name='commercial-detail'),
    # Commercial dashboard
    path('commercial/orders/', views.CommercialOrdersView.as_view(), name='commercial-orders'),
    path('commercial/orders/<str:order_number>/', views.CommercialOrderDetailView.as_view(), name='commercial-order-detail'),
    path('commercial/stats/', views.CommercialStatsView.as_view(), name='commercial-stats'),
    # Assistance interface
    path('assistance/stats/', views.AssistanceStatsView.as_view(), name='assistance-stats'),
    path('assistance/tickets/', views.AssistanceTicketListView.as_view(), name='assistance-tickets'),
    path('assistance/tickets/<int:pk>/', views.AssistanceTicketDetailView.as_view(), name='assistance-ticket-detail'),
    path('assistance/tickets/<int:pk>/messages/', views.AssistanceTicketMessageView.as_view(), name='assistance-ticket-message'),
    path('assistance/disputes/', views.AssistanceDisputeListView.as_view(), name='assistance-disputes'),
    path('assistance/disputes/<int:pk>/', views.AssistanceDisputeDetailView.as_view(), name='assistance-dispute-detail'),
    path('assistance/disputes/<int:pk>/messages/', views.AssistanceDisputeMessageView.as_view(), name='assistance-dispute-message'),
    path('assistance/disputes/<int:pk>/decision/', views.AssistanceDisputeDecisionView.as_view(), name='assistance-dispute-decision'),
    path('assistance/reviews/', views.AssistanceReviewListView.as_view(), name='assistance-reviews'),
    path('assistance/reviews/<int:pk>/action/', views.AssistanceReviewApproveView.as_view(), name='assistance-review-action'),
    path('assistance/sav/', views.AssistanceSavListView.as_view(), name='assistance-sav'),
    path('assistance/sav/<int:pk>/', views.AssistanceSavDetailView.as_view(), name='assistance-sav-detail'),
    path('assistance/sav/<int:pk>/resolve/', views.AssistanceSavResolveView.as_view(), name='assistance-sav-resolve'),
    path('assistance/sav/<int:pk>/messages/', views.AssistanceSavMessageView.as_view(), name='assistance-sav-message'),
]
