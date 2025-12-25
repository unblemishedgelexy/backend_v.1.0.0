from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTP


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('full_name', 'email', 'mobile_number')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Verification', {'fields': ('is_email_verified', 'is_mobile_verified')}),
        ('OAuth', {'fields': ('google_id',)}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'mobile_number', 'password1', 'password2', 'role'),
        }),
    )
    list_display = ('username', 'email', 'mobile_number', 'role', 'is_email_verified', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_email_verified', 'is_mobile_verified')
    search_fields = ('username', 'email', 'mobile_number', 'full_name')
    ordering = ('-date_joined',)


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'verification_type', 'is_verified', 'created_at', 'expires_at')
    list_filter = ('verification_type', 'is_verified', 'created_at')
    search_fields = ('user__username', 'user__email', 'otp_code')
    readonly_fields = ('user', 'otp_code', 'created_at', 'expires_at')
    
    def has_add_permission(self, request):
        return False  # OTPs are created automatically, not manually

