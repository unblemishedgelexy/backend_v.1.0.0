from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [

    # --------------------
    # Core / Status
    # --------------------
    path("", views.home_view, name="home"),

    # --------------------
    # Registration (Email OTP - Redis)
    # --------------------
    path("register/send-otp/", views.send_registration_otp, name="send_registration_otp"),
    path("register/verify-otp/", views.verify_registration_otp, name="verify_registration_otp"),

    # --------------------
    # Auth
    # --------------------
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # --------------------
    # JWT
    # --------------------
    path("token/refresh/", views.refresh_token_view, name="refresh_token"),
    path("token/verify/", views.verify_access_token, name="verify_token"),

    # --------------------
    # Password Reset (FULL Redis)
    # --------------------
    path("password-reset/request/", views.password_reset_request, name="password_reset_request"),
    path("password-reset/verify/", views.password_reset_verify, name="password_reset_verify"),
    path("password-reset/confirm/", views.password_reset_confirm, name="password_reset_confirm"),

    # --------------------
    # Profile
    # --------------------
    path("me/", views.user_profile_view, name="profile"),
    path("me/update/", views.update_profile, name="update_profile"),
    path("me/profile-picture/", views.upload_profile_picture, name="profile_picture"),
    path("me/public-key/", views.register_public_key, name="register_public_key"),

    # --------------------
    # Email Change + Reverify (Redis)
    # --------------------
    path("me/email/change/", views.change_email, name="change_email"),
    path("me/email/verify/", views.verify_email_change, name="verify_email_change"),

    # --------------------
    # Mobile Number (Redis OTP)
    # --------------------
    path("me/mobile/add/", views.add_mobile, name="add_mobile"),
    path("me/mobile/verify/", views.verify_mobile, name="verify_mobile"),

    # --------------------
    # Username
    # --------------------
    path("username/check/", views.check_username, name="check_username"),

    # --------------------
    # Account State
    # --------------------
    path("me/deactivate/", views.deactivate_account, name="deactivate_account"),
    path("me/security/", views.security_info, name="security_info"),

    # --------------------
    # Users (search / list)
    # --------------------
    path("users/", views.users_list, name="users_list"),

    # --------------------
    # OAuth
    # --------------------
    path("google-login/", views.google_login_view, name="google_login"),
]
