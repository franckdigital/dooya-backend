from django.contrib import admin
from .models import Conversation, Message, MessageReaction


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ['sender', 'content', 'type', 'is_read', 'created_at']
    max_num = 20


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'type', 'order', 'created_at', 'updated_at']
    list_filter = ['type']
    search_fields = ['participants__email']
    filter_horizontal = ['participants']
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'sender', 'type', 'is_read', 'created_at']
    list_filter = ['type', 'is_read']
    search_fields = ['sender__email', 'content']
    readonly_fields = ['created_at']


@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ['message', 'user', 'emoji', 'created_at']
