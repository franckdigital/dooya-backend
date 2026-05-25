from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from . import views

urlpatterns = [
    # Santé
    path('health/', views.health_check, name='health-check'),

    # Auth JWT
    path('auth/login/', TokenObtainPairView.as_view(), name='token-obtain'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/verify/', TokenVerifyView.as_view(), name='token-verify'),
    path('auth/register/', views.RegisterView.as_view(), name='register'),

    # Utilisateur connecté
    path('me/', views.MeView.as_view(), name='me'),
    path('me/profile/', views.ProfileView.as_view(), name='my-profile'),
]
