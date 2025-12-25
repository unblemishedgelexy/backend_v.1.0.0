from django.contrib import admin
from .models import E2EEIdentity, DMConversation, DMMessage


@admin.register(E2EEIdentity)
class E2EEIdentityAdmin(admin.ModelAdmin):
    list_display = ("user_id", "created_at", "updated_at")
    search_fields = ("user_id",)


@admin.register(DMConversation)
class DMConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user1_id", "user2_id", "created_at")
    search_fields = ("user1_id", "user2_id")


@admin.register(DMMessage)
class DMMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender_id", "timestamp")
    search_fields = ("sender_id", "conversation__id")
    list_filter = ("timestamp",)
