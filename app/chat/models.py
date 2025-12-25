import uuid
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_group = models.BooleanField(default=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    created_by_id = models.CharField(max_length=100, blank=True, null=True)  # auth server user id
    created_by_username = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{'Group' if self.is_group else 'DM'} - {self.id}"


class ConversationMember(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='members'
    )
    # ALWAYS: auth server user id (string)
    user_id = models.CharField(max_length=100)  # auth server user id
    # Display username
    username = models.CharField(max_length=150)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_admin = models.BooleanField(default=False)

    class Meta:
        unique_together = ('conversation', 'user_id')

    def __str__(self):
        return f"{self.username} in {self.conversation.id}"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender_id = models.CharField(max_length=100)
    sender_username = models.CharField(max_length=150)
    ciphertext = models.TextField()  # Encrypted payload
    metadata = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    delivered_to = models.JSONField(default=list, blank=True)
    read_by = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message {self.id} by {self.sender_username} in {self.conversation_id}"
