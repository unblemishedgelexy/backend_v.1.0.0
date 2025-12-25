import uuid
from django.db import models
from django.utils import timezone


class E2EEIdentity(models.Model):
    """
    Har user ke liye ek E2EE public key (private key client ke paas rahega).
    """
    user_id = models.CharField(max_length=100, unique=True)
    public_key = models.TextField()  # base64 / hex string
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"E2EEIdentity({self.user_id})"


class DMConversation(models.Model):
    """
    1-1 DM conversation. user1_id < user2_id (sorted) store karenge
    takki ek hi pair ke beech multiple DM rows na bane.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user1_id = models.CharField(max_length=100)
    user2_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user1_id", "user2_id")

    def __str__(self):
        return f"DM({self.user1_id}, {self.user2_id})"


class DMMessage(models.Model):
    """
    Pure E2EE message: sirf nonce + ciphertext store hoga.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        DMConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender_id = models.CharField(max_length=100)

    # E2EE fields
    nonce = models.TextField()       # base64 nonce
    ciphertext = models.TextField()  # base64 ciphertext

    metadata = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"DMMessage({self.id}) in {self.conversation_id}"
