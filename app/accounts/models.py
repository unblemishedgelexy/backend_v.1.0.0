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
    
    full_name = models.CharField(max_length=150, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True, null=True, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default='user'
    )
    is_email_verified = models.BooleanField(default=False)
    is_mobile_verified = models.BooleanField(default=False)
    google_id = models.CharField(max_length=200, blank=True, null=True, unique=True)
    # Client-side public key for end-to-end encryption (PEM / base64). Optional.
    public_key = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.username or self.email


class OTP(models.Model):
    """OTP Model for email and SMS verification"""
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
    
    def __str__(self):
        return f"{self.user.username} - {self.verification_type}"
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        return not self.is_expired() and not self.is_verified
    
    @staticmethod
    def create_otp(user, verification_type):
        """Create new OTP for user"""
        import random
        otp_length = int(os.getenv('OTP_LENGTH', 6))
        otp_expiry = int(os.getenv('OTP_EXPIRY_MINUTES', 10))
        
        otp_code = ''.join([str(random.randint(0, 9)) for _ in range(otp_length)])
        expires_at = timezone.now() + timedelta(minutes=otp_expiry)
        
        # Delete old OTPs for this user and type
        OTP.objects.filter(user=user, verification_type=verification_type).delete()
        
        otp = OTP.objects.create(
            user=user,
            otp_code=otp_code,
            verification_type=verification_type,
            expires_at=expires_at
        )
        return otp
