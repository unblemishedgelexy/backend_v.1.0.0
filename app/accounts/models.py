from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
import os


class User(AbstractUser):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('creator', 'Creator'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
    ]

    # Core identity
    email = models.EmailField(unique=True)

    # Profile
    full_name = models.CharField(max_length=150, blank=True)
    username = models.CharField(max_length=150, unique=True, blank=True)
    profile_image = models.URLField(blank=True)  # ImageKit URL

    # Mobile (verified later)
    mobile_number = models.CharField(max_length=20, blank=True, null=True)

    # Role & flags
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='user')
    is_email_verified = models.BooleanField(default=False)
    is_mobile_verified = models.BooleanField(default=False)

    # OAuth
    google_id = models.CharField(max_length=200, blank=True, null=True, unique=True)

    # E2E Encryption
    public_key = models.TextField(blank=True, null=True)

    # Metadata
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username or self.email



class OTP(models.Model):
    VERIFICATION_TYPES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('password_reset', 'Password Reset'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    otp_code = models.CharField(max_length=6)
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPES)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    @staticmethod
    def create_otp(user, verification_type):
        import random
        otp_length = int(os.getenv('OTP_LENGTH', 6))
        otp_expiry = int(os.getenv('OTP_EXPIRY_MINUTES', 10))

        otp_code = ''.join(str(random.randint(0, 9)) for _ in range(otp_length))
        expires_at = timezone.now() + timedelta(minutes=otp_expiry)

        OTP.objects.filter(
            user=user,
            verification_type=verification_type
        ).delete()

        return OTP.objects.create(
            user=user,
            otp_code=otp_code,
            verification_type=verification_type,
            expires_at=expires_at
        )
