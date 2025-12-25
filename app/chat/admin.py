from django.contrib import admin
from .models import Conversation, ConversationMember, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_group', 'name', 'created_by_username', 'created_at')


@admin.register(ConversationMember)
class ConversationMemberAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'username', 'is_admin', 'joined_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender_username', 'timestamp')
