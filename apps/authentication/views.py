from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema
from apps.users.models import OTPCode
from core.utils import generate_otp
from .serializers import (
    RegisterSerializer, LoginSerializer, PhoneLoginSerializer,
    OTPVerifySerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, SocialAuthSerializer,
)

User = get_user_model()


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class AuthRateThrottle(AnonRateThrottle):
    scope = 'auth'
    rate = '10/minute'


@extend_schema(tags=['auth'])
class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        from apps.users.serializers import UserDetailSerializer
        return Response({
            'message': 'Compte créé avec succès. Vérifiez votre email.',
            'tokens': tokens,
            'user': UserDetailSerializer(user, context={'request': request}).data,
        }, status=status.HTTP_201_CREATED)


@extend_schema(tags=['auth'])
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        tokens = get_tokens_for_user(user)
        from apps.users.serializers import UserDetailSerializer
        return Response({
            'tokens': tokens,
            'user': UserDetailSerializer(user, context={'request': request}).data,
        })


@extend_schema(tags=['auth'])
class PhoneLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = PhoneLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone']
        user = User.objects.get(phone=phone)
        otp = generate_otp()
        OTPCode.objects.create(
            user=user, code=otp, purpose='login',
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        from apps.notifications.services.sms import send_sms
        send_sms(str(user.phone), f'Votre code Dooya: {otp}')
        return Response({'message': 'Code OTP envoyé par SMS.'})


@extend_schema(tags=['auth'])
class OTPLoginVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get('phone')
        if not phone:
            return Response({'message': 'Téléphone requis.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response({'message': 'Utilisateur introuvable.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = OTPVerifySerializer(data=request.data, context={'user': user})
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data['otp']
        otp.is_used = True
        otp.save()
        user.is_phone_verified = True
        user.save(update_fields=['is_phone_verified'])
        tokens = get_tokens_for_user(user)
        from apps.users.serializers import UserDetailSerializer
        return Response({'tokens': tokens, 'user': UserDetailSerializer(user, context={'request': request}).data})


@extend_schema(tags=['auth'])
class EmailVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OTPVerifySerializer(
            data={**request.data, 'purpose': 'email_verify'},
            context={'user': request.user}
        )
        serializer.is_valid(raise_exception=True)
        otp = serializer.validated_data['otp']
        otp.is_used = True
        otp.save()
        request.user.is_email_verified = True
        request.user.save(update_fields=['is_email_verified'])
        return Response({'message': 'Email vérifié avec succès.'})


@extend_schema(tags=['auth'])
class ResendOTPView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        purpose = request.data.get('purpose', 'email_verify')
        user = request.user
        otp = generate_otp()
        OTPCode.objects.create(
            user=user, code=otp, purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        if purpose == 'email_verify':
            from apps.notifications.services.email import send_email
            send_email(
                to=user.email, subject='Code de vérification Dooya',
                template='emails/otp.html', context={'otp': otp, 'user': user},
            )
        elif purpose == 'phone_verify' and user.phone:
            from apps.notifications.services.sms import send_sms
            send_sms(str(user.phone), f'Votre code Dooya: {otp}')
        return Response({'message': 'Code envoyé.'})


@extend_schema(tags=['auth'])
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = User.objects.get(email=serializer.validated_data['email'])
            otp = generate_otp()
            OTPCode.objects.create(
                user=user, code=otp, purpose='password_reset',
                expires_at=timezone.now() + timedelta(minutes=15)
            )
            from apps.notifications.services.email import send_email
            send_email(
                to=user.email, subject='Réinitialisation mot de passe Dooya',
                template='emails/password_reset.html', context={'otp': otp, 'user': user},
            )
        except User.DoesNotExist:
            pass
        return Response({'message': 'Si ce compte existe, un email a été envoyé.'})


@extend_schema(tags=['auth'])
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        otp = serializer.validated_data['otp']
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        otp.is_used = True
        otp.save()
        return Response({'message': 'Mot de passe réinitialisé avec succès.'})


@extend_schema(tags=['auth'])
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass
        return Response({'message': 'Déconnexion réussie.'})


@extend_schema(tags=['auth'])
class SocialAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = serializer.validated_data['provider']
        access_token = serializer.validated_data['access_token']

        if provider == 'google':
            user_info = self._get_google_info(access_token)
        elif provider == 'facebook':
            user_info = self._get_facebook_info(access_token)
        else:
            return Response({'message': 'Fournisseur non supporté.'}, status=status.HTTP_400_BAD_REQUEST)

        if not user_info:
            return Response({'message': 'Token invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        user, created = User.objects.get_or_create(
            email=user_info['email'],
            defaults={
                'username': user_info['email'].split('@')[0],
                'first_name': user_info.get('given_name', ''),
                'last_name': user_info.get('family_name', ''),
                'is_email_verified': True,
            }
        )
        tokens = get_tokens_for_user(user)
        from apps.users.serializers import UserDetailSerializer
        return Response({
            'tokens': tokens,
            'user': UserDetailSerializer(user, context={'request': request}).data,
            'created': created,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def _get_google_info(self, token):
        import requests
        res = requests.get(f'https://www.googleapis.com/oauth2/v1/userinfo?access_token={token}', timeout=10)
        return res.json() if res.ok else None

    def _get_facebook_info(self, token):
        import requests
        res = requests.get(f'https://graph.facebook.com/me?fields=id,email,first_name,last_name&access_token={token}', timeout=10)
        return res.json() if res.ok else None
