from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Home
    path('', views.home_view, name='home'),
    
    # Registration with OTP
    path('register/send-otp/', views.send_registration_otp, name='send_registration_otp'),
    path('register/verify-otp/', views.verify_registration_otp, name='verify_registration_otp'),
    
    # Login/Logout
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('users/', views.users_list, name='users_list'),
    
    # Token Refresh
    path('token/refresh/', views.refresh_token_view, name='refresh_token'),
    path('token/verify/', views.verify_access_token, name='verify_token'),
    
    # Password Reset
    path('password-reset/request/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/verify/', views.password_reset_verify, name='password_reset_verify'),
    path('password-reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'),
    
    # User Profile
    path('me/', views.user_profile_view, name='profile'),
    path('me/public-key/', views.register_public_key, name='register_public_key'),
    
    # Google OAuth2
    path('google-login/', views.google_login_view, name='google_login'),
]
