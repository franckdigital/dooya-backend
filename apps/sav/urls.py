from django.urls import path
from . import views

app_name = 'sav'

urlpatterns = [
    # Client
    path('', views.MySavRequestListCreateView.as_view(), name='my-sav-list'),
    path('<int:pk>/', views.MySavRequestDetailView.as_view(), name='my-sav-detail'),
    path('<int:pk>/cancel/', views.MySavRequestCancelView.as_view(), name='my-sav-cancel'),
    path('<int:pk>/messages/', views.SavMessageCreateView.as_view(), name='sav-message'),

    # Admin
    path('admin/', views.AdminSavListView.as_view(), name='admin-sav-list'),
    path('admin/<int:pk>/', views.AdminSavDetailView.as_view(), name='admin-sav-detail'),
    path('admin/<int:pk>/resolve/', views.AdminSavResolveView.as_view(), name='admin-sav-resolve'),
]
