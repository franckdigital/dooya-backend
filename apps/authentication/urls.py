from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('login/phone/', views.PhoneLoginView.as_view(), name='phone-login'),
    path('login/phone/verify/', views.OTPLoginVerifyView.as_view(), name='otp-login-verify'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('verify/email/', views.EmailVerifyView.as_view(), name='email-verify'),
    path('verify/resend/', views.ResendOTPView.as_view(), name='otp-resend'),
    path('password/reset/', views.PasswordResetRequestView.as_view(), name='password-reset'),
    path('password/reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('social/', views.SocialAuthView.as_view(), name='social-auth'),
]
