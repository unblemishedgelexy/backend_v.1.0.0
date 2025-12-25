from django.urls import path
from .views import imagekit_auth

urlpatterns = [
    path("imagekit/auth/", imagekit_auth),
]