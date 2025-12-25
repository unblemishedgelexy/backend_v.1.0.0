"""
Custom SimpleJWT token classes to include username in access token
"""
from datetime import timedelta
from django.conf import settings
from rest_framework_simplejwt.tokens import Token, AccessToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomAccessToken(AccessToken):
    """Custom access token that includes username and email"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only add claims if this is a new token (self.token is None after __init__)
        if hasattr(self, 'user') and self.user:
            self['username'] = str(self.user.username)
            self['email'] = str(self.user.email) if self.user.email else None


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom serializer that uses CustomAccessToken"""
    @classmethod
    def get_token(cls, user):
        token = CustomAccessToken.for_user(user)
        return token
