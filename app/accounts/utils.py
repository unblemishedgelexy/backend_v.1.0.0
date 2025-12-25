"""Utilities for sending OTP via Email and SMS"""
import os
from django.core.mail import send_mail
from django.conf import settings

try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False


def send_email_otp(email, otp_code):
    """Send OTP via Email"""
    subject = "Your OTP for Email Verification"
    message = f"""
    Your OTP is: {otp_code}
    
    This OTP will expire in 10 minutes.
    Do not share this OTP with anyone.
    
    If you didn't request this, please ignore this email.
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return True, "OTP sent to email successfully"
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"


def send_sms_otp(phone_number, otp_code):
    """Send OTP via SMS using Twilio"""
    if not TWILIO_AVAILABLE:
        return False, "Twilio not installed"
    
    try:
        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        from_number = settings.TWILIO_PHONE_NUMBER
        
        if not account_sid or not auth_token:
            return False, "Twilio credentials not configured"
        
        client = Client(account_sid, auth_token)
        
        message_body = f"Your OTP is: {otp_code}. This will expire in 10 minutes. Do not share with anyone."
        
        message = client.messages.create(
            body=message_body,
            from_=from_number,
            to=phone_number
        )
        
        return True, f"OTP sent to SMS successfully (SID: {message.sid})"
    except Exception as e:
        return False, f"Failed to send SMS: {str(e)}"


def send_otp(user, verification_type, medium='both'):
    """
    Send OTP via Email and/or SMS
    
    Args:
        user: User object
        verification_type: 'email', 'sms', or 'password_reset'
        medium: 'email', 'sms', or 'both'
    """
    from .models import OTP
    
    # Create OTP
    otp = OTP.create_otp(user, verification_type)
    
    results = {}
    
    # Send via Email
    if medium in ['email', 'both']:
        success, message = send_email_otp(user.email, otp.otp_code)
        results['email'] = {'success': success, 'message': message}
    
    # Send via SMS
    if medium in ['sms', 'both'] and user.mobile_number:
        success, message = send_sms_otp(user.mobile_number, otp.otp_code)
        results['sms'] = {'success': success, 'message': message}
    
    return otp, results
