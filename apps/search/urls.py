from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    path('', views.TextSearchView.as_view(), name='text-search'),
    path('voice/', views.VoiceSearchView.as_view(), name='voice-search'),
    path('suggestions/', views.SearchSuggestionsView.as_view(), name='suggestions'),
]
