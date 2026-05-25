from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/', views.CartAddView.as_view(), name='cart-add'),
    path('cart/clear/', views.CartClearView.as_view(), name='cart-clear'),
    path('cart/sync/', views.CartSyncView.as_view(), name='cart-sync'),
    path('cart/items/<int:item_id>/', views.CartItemUpdateView.as_view(), name='cart-item-update'),
]
