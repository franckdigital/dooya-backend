from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.utils import timezone
from datetime import timedelta
from apps.users.models import OTPCode
from core.utils import generate_otp

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'phone', 'password', 'password_confirm', 'role']
        extra_kwargs = {
            'role': {'required': False},
            'phone': {'required': False},
        }

    def validate_role(self, value):
        if value == 'admin':
            raise serializers.ValidationError('Impossible de créer un compte administrateur.')
        return value

    def validate(self, data):
        if data['password'] != data.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Les mots de passe ne correspondent pas.'})
        return data

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        self._send_verification(user)
        return user

    def _send_verification(self, user):
        otp = generate_otp()
        OTPCode.objects.create(
            user=user, code=otp, purpose='email_verify',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        from apps.notifications.services.email import send_email
        send_email(
            to=user.email,
            subject='Vérifiez votre compte Dooya',
            template='emails/verify_email.html',
            context={'user': user, 'otp': otp},
        )


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()   # accepts email OR username
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        identifier = data['username'].strip()
        password   = data['password']
        request    = self.context.get('request')

        user = None
        if '@' in identifier:
            try:
                u = User.objects.get(email__iexact=identifier)
                user = authenticate(request=request, email=u.email, password=password)
            except User.DoesNotExist:
                pass
        else:
            try:
                u = User.objects.get(username__iexact=identifier)
                user = authenticate(request=request, email=u.email, password=password)
            except User.DoesNotExist:
                pass

        if not user:
            raise serializers.ValidationError('Identifiants incorrects.')
        if not user.is_active:
            raise serializers.ValidationError('Ce compte est désactivé.')
        data['user'] = user
        return data


class PhoneLoginSerializer(serializers.Serializer):
    phone = serializers.CharField()

    def validate_phone(self, value):
        from apps.users.models import User
        try:
            User.objects.get(phone=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('Aucun compte associé à ce numéro.')
        return value


class OTPVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)
    purpose = serializers.ChoiceField(choices=['phone_verify', 'email_verify', 'password_reset', 'login'])

    def validate(self, data):
        user = self.context.get('user')
        if not user:
            raise serializers.ValidationError('Utilisateur requis.')
        otp = OTPCode.objects.filter(
            user=user, code=data['code'], purpose=data['purpose'], is_used=False
        ).first()
        if not otp or otp.is_expired:
            raise serializers.ValidationError({'code': 'Code OTP invalide ou expiré.'})
        data['otp'] = otp
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Les mots de passe ne correspondent pas.'})
        try:
            user = User.objects.get(email=data['email'])
        except User.DoesNotExist:
            raise serializers.ValidationError({'email': 'Aucun compte trouvé.'})
        otp = OTPCode.objects.filter(
            user=user, code=data['code'], purpose='password_reset', is_used=False
        ).first()
        if not otp or otp.is_expired:
            raise serializers.ValidationError({'code': 'Code invalide ou expiré.'})
        data['user'] = user
        data['otp'] = otp
        return data


class SocialAuthSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['google', 'facebook'])
    access_token = serializers.CharField()


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = serializers.SerializerMethodField()

    def get_user(self, obj):
        from apps.users.serializers import UserDetailSerializer
        return UserDetailSerializer(obj['user'], context=self.context).data
