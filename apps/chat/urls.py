from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('conversations/', views.ConversationListView.as_view(), name='conversation-list'),
    path('conversations/create/', views.ConversationCreateView.as_view(), name='conversation-create'),
    path('conversations/search/', views.ConversationSearchView.as_view(), name='conversation-search'),
    path('conversations/<int:pk>/', views.ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<int:pk>/messages/', views.MessageCreateView.as_view(), name='message-create'),
    path('conversations/<int:pk>/voice/', views.VoiceMessageView.as_view(), name='voice-message'),
    path('conversations/<int:pk>/read/', views.MessageReadView.as_view(), name='message-read'),
    # Admin support endpoints
    path('admin/conversations/', views.AdminConversationListView.as_view(), name='admin-conversation-list'),
    path('admin/conversations/<int:pk>/', views.AdminConversationDetailView.as_view(), name='admin-conversation-detail'),
    path('admin/conversations/<int:pk>/messages/', views.AdminMessageCreateView.as_view(), name='admin-message-create'),
    path('admin/conversations/<int:pk>/read/', views.AdminMessageReadView.as_view(), name='admin-message-read'),
]
