from django.urls import path
from . import views
from .views import CourierProfileView, CourierAvailabilityView, DeliveryPersonActiveListView, CourierLocationUpdateView

app_name = 'deliveries'

urlpatterns = [
    path('delivery-zones/', views.DeliveryZoneListView.as_view(), name='delivery-zone-list'),
    path('delivery-zones/calculate/', views.DeliveryZoneCalculateView.as_view(), name='delivery-zone-calculate'),
    path('relay-points/', views.RelayPointListView.as_view(), name='relay-point-list'),
    path('relay-points/<int:pk>/', views.RelayPointDetailView.as_view(), name='relay-point-detail'),
    path('track/<str:tracking_number>/', views.TrackingView.as_view(), name='tracking'),
    path('delivery/my/', views.DeliveryPersonListView.as_view(), name='delivery-my-list'),
    path('delivery/<int:pk>/status/', views.DeliveryUpdateStatusView.as_view(), name='delivery-status'),
    path('delivery/<int:pk>/signature/', views.DeliverySignatureView.as_view(), name='delivery-signature'),
    path('delivery/qr-validate/', views.QRValidateView.as_view(), name='qr-validate'),
    # Courier profile, availability & location
    path('courier/profile/', CourierProfileView.as_view(), name='courier-profile'),
    path('courier/availability/', CourierAvailabilityView.as_view(), name='courier-availability'),
    path('courier/location/', CourierLocationUpdateView.as_view(), name='courier-location'),
    # Dashboard livreur
    path('delivery/dashboard/', views.DeliveryPersonDashboardView.as_view(), name='delivery-dashboard'),
    path('delivery/<int:pk>/detail/', views.DeliveryPersonDetailView.as_view(), name='delivery-detail'),
    path('delivery/<int:pk>/pickup/', views.DeliveryPersonPickupView.as_view(), name='delivery-pickup'),
    path('delivery/<int:pk>/gps/', views.DeliveryPersonUpdateGPSView.as_view(), name='delivery-gps'),
    path('delivery/active/', DeliveryPersonActiveListView.as_view(), name='delivery-active'),
    path('delivery/history/', views.DeliveryPersonHistoryView.as_view(), name='delivery-history'),

    # Admin
    path('admin/deliveries/', views.AdminDeliveryListView.as_view(), name='admin-delivery-list'),
    path('admin/deliveries/<int:pk>/', views.AdminDeliveryDetailView.as_view(), name='admin-delivery-detail'),
    path('admin/deliveries/<int:pk>/assign/', views.AdminAssignDeliveryView.as_view(), name='admin-delivery-assign'),
    path('admin/deliveries/<int:pk>/reassign/', views.AdminReassignDeliveryView.as_view(), name='admin-delivery-reassign'),
    path('admin/relay-points/', views.AdminRelayPointListCreateView.as_view(), name='admin-relay-point-list'),
    path('admin/relay-points/<int:pk>/', views.AdminRelayPointDetailView.as_view(), name='admin-relay-point-detail'),
    path('admin/delivery-zones/', views.AdminDeliveryZoneListCreateView.as_view(), name='admin-zone-list'),
    path('admin/delivery-zones/<int:pk>/', views.AdminDeliveryZoneDetailView.as_view(), name='admin-zone-detail'),
    path('admin/delivery-persons/', views.AdminDeliveryPersonListView.as_view(), name='admin-delivery-persons'),
    path('admin/delivery-persons/<int:pk>/', views.AdminDeliveryPersonDetailView.as_view(), name='admin-delivery-person-detail'),

    # Client
    path('orders/<str:order_number>/delivery/', views.ClientDeliveryByOrderView.as_view(), name='client-delivery-by-order'),
    path('orders/<str:order_number>/delivery/update/', views.ClientUpdateDeliveryAddressView.as_view(), name='client-delivery-update'),
]
