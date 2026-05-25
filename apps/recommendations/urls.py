from django.urls import path
from . import views

app_name = 'recommendations'

urlpatterns = [
    path('trending/', views.TrendingView.as_view(), name='trending'),
    path('personalized/', views.PersonalizedView.as_view(), name='personalized'),
    path('recently-viewed/', views.RecentlyViewedView.as_view(), name='recently-viewed'),
    path('products/<slug:slug>/similar/', views.SimilarProductsView.as_view(), name='similar'),
    path('products/<slug:slug>/bought-together/', views.FrequentlyBoughtTogetherView.as_view(), name='bought-together'),
    path('stores/<slug:slug>/trending/', views.TrendingByStoreView.as_view(), name='store-trending'),
]
