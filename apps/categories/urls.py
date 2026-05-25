from django.urls import path
from . import views

app_name = 'categories'

urlpatterns = [
    # Admin (MUST come before slug patterns to avoid <slug:slug>/ capturing "admin")
    path('admin/', views.AdminCategoryListCreateView.as_view(), name='admin-category-list'),
    path('admin/<int:pk>/', views.AdminCategoryDetailView.as_view(), name='admin-category-detail'),
    path('admin/attributes/', views.AdminAttributeListCreateView.as_view(), name='admin-attribute-list'),
    path('admin/attributes/<int:pk>/', views.AdminAttributeDetailView.as_view(), name='admin-attribute-detail'),

    # Public
    path('tree/', views.CategoryTreeView.as_view(), name='category-tree'),
    path('', views.CategoryListView.as_view(), name='category-list'),
    path('<slug:slug>/', views.CategoryDetailView.as_view(), name='category-detail'),
    path('<slug:slug>/subcategories/', views.SubcategoryListView.as_view(), name='subcategory-list'),
    path('<slug:slug>/filters/', views.CategoryFiltersView.as_view(), name='category-filters'),
    path('<slug:slug>/products/', views.CategoryProductsView.as_view(), name='category-products'),
]
