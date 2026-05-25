from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    # Avis produits
    path('products/<slug:slug>/reviews/', views.ProductReviewListView.as_view(), name='product-review-list'),
    path('products/<slug:slug>/reviews/summary/', views.ProductReviewSummaryView.as_view(), name='product-review-summary'),
    path('products/<slug:slug>/reviews/create/', views.ProductReviewCreateView.as_view(), name='product-review-create'),
    path('reviews/<int:pk>/update/', views.ProductReviewUpdateView.as_view(), name='product-review-update'),
    path('reviews/<int:pk>/delete/', views.ProductReviewDeleteView.as_view(), name='product-review-delete'),
    path('reviews/<int:pk>/helpful/', views.ReviewHelpfulView.as_view(), name='review-helpful'),
    path('reviews/<int:pk>/reply/', views.VendorReplyView.as_view(), name='vendor-reply'),

    # Avis boutiques
    path('stores/<slug:slug>/reviews/', views.StoreReviewListView.as_view(), name='store-review-list'),
    path('stores/<slug:slug>/reviews/create/', views.StoreReviewCreateView.as_view(), name='store-review-create'),

    # Mes avis
    path('my/', views.MyReviewListView.as_view(), name='my-reviews'),

    # Admin
    path('admin/', views.AdminReviewListView.as_view(), name='admin-review-list'),
    path('admin/<int:pk>/approve/', views.AdminReviewApproveView.as_view(), name='admin-review-approve'),
]
