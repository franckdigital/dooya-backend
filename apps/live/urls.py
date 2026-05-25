from django.urls import path
from . import views

app_name = 'live'

urlpatterns = [
    # Public
    path('', views.LiveSessionPublicListView.as_view(), name='public-list'),
    path('<int:pk>/', views.LiveSessionPublicDetailView.as_view(), name='public-detail'),
    path('room/<str:room_id>/', views.LiveSessionByRoomView.as_view(), name='by-room'),
    path('<int:session_pk>/comments/', views.LiveCommentListView.as_view(), name='comment-list'),

    # Vendor
    path('vendor/', views.VendorLiveSessionListView.as_view(), name='vendor-list'),
    path('vendor/<int:pk>/', views.VendorLiveSessionDetailView.as_view(), name='vendor-detail'),
    path('vendor/<int:pk>/start/', views.VendorLiveStartView.as_view(), name='vendor-start'),
    path('vendor/<int:pk>/end/', views.VendorLiveEndView.as_view(), name='vendor-end'),
    path('vendor/<int:session_pk>/products/', views.VendorLiveProductListView.as_view(), name='vendor-products'),
    path('vendor/<int:session_pk>/products/<int:pk>/', views.VendorLiveProductDetailView.as_view(), name='vendor-product-detail'),
    path('vendor/<int:session_pk>/products/<int:pk>/feature/', views.VendorFeatureProductView.as_view(), name='vendor-feature'),

    # Admin
    path('admin/', views.AdminLiveSessionListView.as_view(), name='admin-list'),
    path('admin/<int:pk>/', views.AdminLiveSessionDetailView.as_view(), name='admin-detail'),
]
