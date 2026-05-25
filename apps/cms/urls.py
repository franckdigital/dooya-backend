from django.urls import path
from . import views

app_name = 'cms'

urlpatterns = [
    path('pages/<slug:slug>/', views.PageDetailView.as_view(), name='page-detail'),
    path('sliders/', views.SliderListView.as_view(), name='slider-list'),
    path('banners/', views.BannerListView.as_view(), name='banner-list'),
    path('banners/<int:pk>/click/', views.BannerClickView.as_view(), name='banner-click'),
    path('blog/', views.BlogPostListView.as_view(), name='blog-list'),
    path('blog/<slug:slug>/', views.BlogPostDetailView.as_view(), name='blog-detail'),
    path('coupons/validate/', views.CouponValidateView.as_view(), name='coupon-validate'),
    path('admin/pages/', views.AdminPageView.as_view(), name='admin-page-list'),
    path('admin/pages/<int:pk>/', views.AdminPageView.as_view(), name='admin-page-detail'),
    path('admin/sliders/', views.AdminSliderView.as_view(), name='admin-slider-list'),
    path('admin/sliders/<int:pk>/', views.AdminSliderView.as_view(), name='admin-slider-detail'),
    path('sidebar-cards/', views.SidebarCardListView.as_view(), name='sidebar-card-list'),
    path('admin/sidebar-cards/', views.AdminSidebarCardView.as_view(), name='admin-sidebar-card-list'),
    path('admin/sidebar-cards/<int:pk>/', views.AdminSidebarCardView.as_view(), name='admin-sidebar-card-detail'),
    path('admin/banners/', views.AdminBannerView.as_view(), name='admin-banner-list'),
    path('admin/banners/<int:pk>/', views.AdminBannerView.as_view(), name='admin-banner-detail'),
    path('admin/blog/', views.AdminBlogPostView.as_view(), name='admin-blog-list'),
    path('admin/blog/<int:pk>/', views.AdminBlogPostView.as_view(), name='admin-blog-detail'),
    path('admin/coupons/', views.AdminCouponView.as_view(), name='admin-coupon-list'),
    path('admin/coupons/<int:pk>/', views.AdminCouponView.as_view(), name='admin-coupon-detail'),
    path('admin/blog-categories/', views.BlogCategoryListView.as_view(), name='admin-blog-categories'),
]
