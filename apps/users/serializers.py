from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Address, Favorite, CommercialProfile

User = get_user_model()


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar', 'role']


class UserDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'avatar', 'role', 'language',
            'is_phone_verified', 'is_email_verified',
            'is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login',
            'password',
        ]
        read_only_fields = ['id', 'email', 'role', 'is_phone_verified', 'is_email_verified', 'is_staff', 'is_superuser', 'date_joined']

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=['password'])
        return instance


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'phone', 'avatar', 'language']

    def validate_phone(self, value):
        qs = User.objects.filter(phone=value).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ce numéro de téléphone est déjà utilisé.')
        return value


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class FavoriteSerializer(serializers.ModelSerializer):
    product = serializers.SerializerMethodField()

    class Meta:
        model = Favorite
        fields = ['id', 'product', 'created_at']

    def get_product(self, obj):
        from apps.products.serializers import ProductListSerializer
        return ProductListSerializer(obj.product, context=self.context).data


class CommercialProfileSerializer(serializers.ModelSerializer):
    # Used when linking to an existing user (optional)
    user_id = serializers.IntegerField(write_only=True, required=False)
    # Used when creating a brand-new user inline
    first_name = serializers.CharField(write_only=True, required=False, default='')
    last_name  = serializers.CharField(write_only=True, required=False, default='')
    email      = serializers.EmailField(write_only=True, required=False)
    password   = serializers.CharField(write_only=True, required=False)

    user_name  = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_linked_id = serializers.IntegerField(source='user.id', read_only=True)
    category_ids   = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    category_names = serializers.SerializerMethodField()

    class Meta:
        model = CommercialProfile
        fields = [
            'id', 'user_id', 'user_linked_id', 'user_name', 'user_email',
            'first_name', 'last_name', 'email', 'password',
            'category_ids', 'category_names',
            'notes', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'user_linked_id']

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    def get_category_names(self, obj):
        return [{'id': c.id, 'name': c.name} for c in obj.categories.all()]

    def validate(self, data):
        # On creation: either user_id OR (email + password + first_name) must be provided
        if not self.instance:
            user_id = data.get('user_id')
            email   = data.get('email')
            password = data.get('password')
            if not user_id and not email:
                raise serializers.ValidationError({'email': 'Email requis pour créer un nouveau compte.'})
            if not user_id and not password:
                raise serializers.ValidationError({'password': 'Mot de passe requis pour créer un nouveau compte.'})
            if not user_id and User.objects.filter(email=email).exists():
                raise serializers.ValidationError({'email': 'Un compte avec cet email existe déjà.'})
        return data

    def create(self, validated_data):
        category_ids = validated_data.pop('category_ids', [])
        user_id    = validated_data.pop('user_id', None)
        first_name = validated_data.pop('first_name', '')
        last_name  = validated_data.pop('last_name', '')
        email      = validated_data.pop('email', None)
        password   = validated_data.pop('password', None)

        if user_id:
            user = User.objects.get(pk=user_id)
        else:
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                username=email,
            )
        user.role = 'commercial'
        user.save(update_fields=['role'])
        profile = CommercialProfile.objects.create(user=user, **validated_data)
        if category_ids:
            profile.categories.set(category_ids)
        return profile

    def update(self, instance, validated_data):
        category_ids = validated_data.pop('category_ids', None)
        for key in ('user_id', 'first_name', 'last_name', 'email', 'password'):
            validated_data.pop(key, None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if category_ids is not None:
            instance.categories.set(category_ids)
        return instance
