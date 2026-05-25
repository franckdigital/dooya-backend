from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import DeliveryZone, RelayPoint, Delivery, DeliveryHistory, DeliveryProfile

User = get_user_model()


class DeliveryZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZone
        fields = ['id', 'name', 'cities', 'base_price', 'price_per_kg', 'estimated_days', 'is_active']


class RelayPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelayPoint
        fields = ['id', 'name', 'address', 'city', 'country', 'manager_name', 'phone', 'latitude', 'longitude', 'delivery_price', 'is_active', 'schedule']


class DeliveryHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryHistory
        fields = ['id', 'status', 'location', 'note', 'created_at']


class DeliverySerializer(serializers.ModelSerializer):
    history = DeliveryHistorySerializer(many=True, read_only=True)
    delivery_person_name = serializers.CharField(source='delivery_person.full_name', read_only=True)
    relay_point_name = serializers.CharField(source='relay_point.name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = [
            'id', 'order', 'order_number', 'customer_name',
            'delivery_person', 'delivery_person_name',
            'relay_point', 'relay_point_name', 'type', 'status', 'tracking_number',
            'current_latitude', 'current_longitude', 'estimated_delivery_date',
            'actual_delivery_date', 'delivery_address', 'delivery_notes', 'signature_image', 'qr_code',
            'history', 'created_at', 'updated_at',
        ]
        read_only_fields = ['tracking_number', 'qr_code', 'customer_name', 'created_at', 'updated_at']

    def get_customer_name(self, obj):
        try:
            order = obj.order
            if order.user:
                return order.user.get_full_name() or order.user.email
            addr = order.shipping_address or {}
            return addr.get('full_name') or '—'
        except Exception:
            return None


class DeliveryTrackingSerializer(serializers.ModelSerializer):
    history = DeliveryHistorySerializer(many=True, read_only=True)
    relay_point_name = serializers.CharField(source='relay_point.name', read_only=True)
    relay_point_address = serializers.CharField(source='relay_point.address', read_only=True)
    relay_point_phone = serializers.CharField(source='relay_point.phone', read_only=True)
    relay_point_latitude = serializers.DecimalField(source='relay_point.latitude', max_digits=9, decimal_places=6, read_only=True)
    relay_point_longitude = serializers.DecimalField(source='relay_point.longitude', max_digits=9, decimal_places=6, read_only=True)

    class Meta:
        model = Delivery
        fields = [
            'tracking_number', 'type', 'status', 'delivery_address',
            'relay_point_name', 'relay_point_address', 'relay_point_phone',
            'relay_point_latitude', 'relay_point_longitude',
            'estimated_delivery_date', 'actual_delivery_date',
            'current_latitude', 'current_longitude', 'history',
        ]


class DeliveryPersonSerializer(serializers.Serializer):
    """Lecture seule — agrège User + DeliveryProfile."""
    id = serializers.IntegerField(read_only=True)
    first_name  = serializers.CharField(read_only=True)
    last_name   = serializers.CharField(read_only=True)
    email       = serializers.EmailField(read_only=True)
    phone       = serializers.SerializerMethodField()
    vehicle_type     = serializers.SerializerMethodField()
    coverage_zones   = serializers.SerializerMethodField()
    active_deliveries = serializers.IntegerField(read_only=True)
    total_delivered   = serializers.IntegerField(read_only=True)
    is_active   = serializers.BooleanField(read_only=True)
    notes       = serializers.SerializerMethodField()

    def get_phone(self, obj):
        return str(obj.phone or '')

    def get_vehicle_type(self, obj):
        profile = getattr(obj, 'delivery_profile', None)
        return profile.vehicle_type if profile else 'moto'

    def get_coverage_zones(self, obj):
        profile = getattr(obj, 'delivery_profile', None)
        if not profile:
            return []
        return list(profile.coverage_zones.values('id', 'name'))

    def get_notes(self, obj):
        profile = getattr(obj, 'delivery_profile', None)
        return profile.notes if profile else ''


class DeliveryPersonWriteSerializer(serializers.Serializer):
    """Création/modification d'un livreur + profil."""
    first_name     = serializers.CharField()
    last_name      = serializers.CharField()
    email          = serializers.EmailField()
    password       = serializers.CharField(required=False, write_only=True, allow_blank=True)
    phone          = serializers.CharField(required=False, allow_blank=True)
    vehicle_type   = serializers.ChoiceField(choices=['moto', 'voiture', 'velo', 'pied', 'other'], default='moto')
    coverage_zones = serializers.ListField(child=serializers.IntegerField(), required=False)
    notes          = serializers.CharField(required=False, allow_blank=True)
    is_active      = serializers.BooleanField(default=True)

    def validate_email(self, value):
        qs = User.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Cet email est déjà utilisé.')
        return value

    def validate(self, data):
        if not self.instance and not data.get('password'):
            raise serializers.ValidationError({'password': 'Le mot de passe est requis pour créer un livreur.'})
        return data

    def create(self, validated_data):
        zones = validated_data.pop('coverage_zones', [])
        password = validated_data.pop('password', None)
        phone = validated_data.pop('phone', '')
        notes = validated_data.pop('notes', '')
        vehicle_type = validated_data.pop('vehicle_type', 'moto')
        user = User(
            role='delivery',
            username=validated_data['email'],
            is_email_verified=True,
            **{k: v for k, v in validated_data.items() if k in ('first_name', 'last_name', 'email', 'is_active')},
        )
        if phone:
            user.phone = phone
        user.set_password(password)
        user.save()
        profile = DeliveryProfile.objects.create(user=user, vehicle_type=vehicle_type, notes=notes)
        if zones:
            profile.coverage_zones.set(DeliveryZone.objects.filter(id__in=zones))
        return user

    def update(self, instance, validated_data):
        zones = validated_data.pop('coverage_zones', None)
        password = validated_data.pop('password', None)
        phone = validated_data.pop('phone', None)
        notes = validated_data.pop('notes', None)
        vehicle_type = validated_data.pop('vehicle_type', None)
        for attr in ('first_name', 'last_name', 'email', 'is_active'):
            if attr in validated_data:
                setattr(instance, attr, validated_data[attr])
        if phone is not None:
            instance.phone = phone
        if password:
            instance.set_password(password)
            instance.is_email_verified = True
        instance.save()
        profile, _ = DeliveryProfile.objects.get_or_create(user=instance)
        if vehicle_type:
            profile.vehicle_type = vehicle_type
        if notes is not None:
            profile.notes = notes
        profile.save()
        if zones is not None:
            profile.coverage_zones.set(DeliveryZone.objects.filter(id__in=zones))
        return instance
