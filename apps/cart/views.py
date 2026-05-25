from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer, AddToCartSerializer


def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)
    return cart


@extend_schema(tags=['cart'])
class CartView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cart = get_or_create_cart(request)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)


@extend_schema(tags=['cart'])
class CartAddView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        cart = get_or_create_cart(request)
        product = serializer.validated_data['product']
        variant = serializer.validated_data['variant']
        quantity = serializer.validated_data['quantity']

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            defaults={'quantity': quantity},
        )
        if not created:
            available = variant.stock if variant else product.stock
            new_qty = item.quantity + quantity
            if new_qty > available:
                return Response({'detail': f'Stock insuffisant. Disponible: {available}'}, status=status.HTTP_400_BAD_REQUEST)
            item.quantity = new_qty
            item.save(update_fields=['quantity'])

        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=['cart'])
class CartItemUpdateView(APIView):
    permission_classes = [AllowAny]

    def get_cart_item(self, request, item_id):
        cart = get_or_create_cart(request)
        try:
            return CartItem.objects.get(pk=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return None

    def patch(self, request, item_id):
        item = self.get_cart_item(request, item_id)
        if not item:
            return Response({'detail': 'Article introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        quantity = request.data.get('quantity')
        if not quantity or int(quantity) < 1:
            return Response({'detail': 'Quantité invalide.'}, status=status.HTTP_400_BAD_REQUEST)
        quantity = int(quantity)
        available = item.variant.stock if item.variant else item.product.stock
        if quantity > available:
            return Response({'detail': f'Stock insuffisant. Disponible: {available}'}, status=status.HTTP_400_BAD_REQUEST)
        item.quantity = quantity
        item.save(update_fields=['quantity'])
        cart = item.cart
        return Response(CartSerializer(cart, context={'request': request}).data)

    def delete(self, request, item_id):
        item = self.get_cart_item(request, item_id)
        if not item:
            return Response({'detail': 'Article introuvable.'}, status=status.HTTP_404_NOT_FOUND)
        cart = item.cart
        item.delete()
        return Response(CartSerializer(cart, context={'request': request}).data)


@extend_schema(tags=['cart'])
class CartClearView(APIView):
    permission_classes = [AllowAny]

    def delete(self, request):
        cart = get_or_create_cart(request)
        cart.items.all().delete()
        return Response({'detail': 'Panier vidé.'})


@extend_schema(tags=['cart'])
class CartSyncView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_key = request.data.get('session_key') or request.session.session_key
        if not session_key:
            return Response({'detail': 'session_key requis.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            session_cart = Cart.objects.get(session_key=session_key, user=None)
        except Cart.DoesNotExist:
            user_cart, _ = Cart.objects.get_or_create(user=request.user)
            return Response(CartSerializer(user_cart, context={'request': request}).data)

        user_cart, _ = Cart.objects.get_or_create(user=request.user)
        for item in session_cart.items.all():
            existing = CartItem.objects.filter(cart=user_cart, product=item.product, variant=item.variant).first()
            if existing:
                existing.quantity += item.quantity
                existing.save(update_fields=['quantity'])
            else:
                CartItem.objects.create(
                    cart=user_cart,
                    product=item.product,
                    variant=item.variant,
                    quantity=item.quantity,
                )
        session_cart.delete()
        return Response(CartSerializer(user_cart, context={'request': request}).data)
