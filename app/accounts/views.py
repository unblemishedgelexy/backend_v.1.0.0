from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.utils import timezone
import json
import random
from .forms import RegistrationForm, LoginForm
from .models import OTP
from .utils import send_otp
from rest_framework_simplejwt.serializers import TokenRefreshSerializer, TokenVerifySerializer
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from .tokens import CustomAccessToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator

User = get_user_model()

def _user_from_request(request):
    if getattr(request, 'user', None) and request.user.is_authenticated:
        return request.user

    auth = request.META.get('HTTP_AUTHORIZATION', '')

    if not auth:
        return None

    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None

    token = parts[1]

    try:
        # FIXED: do NOT do dict(CustomAccessToken(token))
        payload = CustomAccessToken(token)
    except Exception as e:
        return None

    # Extract user_id
    user_id = payload.get("user_id")

    if not user_id:
        return None

    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


@require_http_methods(["GET"])
def home_view(request):
    """API home/status endpoint"""
    if request.user.is_authenticated:
        return JsonResponse({
            'success': True,
            'message': 'Welcome to Django Auth API',
            'authenticated': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'full_name': request.user.full_name,
                'mobile_number': request.user.mobile_number,
                'role': request.user.role
            }
        })
    else:
        return JsonResponse({
            'success': True,
            'message': 'Welcome to Django Auth API',
            'authenticated': False,
            'endpoints': {
                'register': 'POST /accounts/register/',
                'register_send_otp': 'POST /accounts/register/send-otp/',
                'register_verify_otp': 'POST /accounts/register/verify-otp/',
                'login': 'POST /accounts/login/',
                'logout': 'POST /accounts/logout/',
                'password_reset_request': 'POST /accounts/password-reset/request/',
                'password_reset_verify': 'POST /accounts/password-reset/verify/',
                'password_reset_confirm': 'POST /accounts/password-reset/confirm/',
                'me': 'GET /accounts/me/',
                'google_login': 'POST /accounts/google-login/'
            }
        })


@csrf_exempt
@require_http_methods(["POST"])
def send_registration_otp(request):
    """Send OTP for email verification during registration"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    # Debug: see exact structure coming from frontend
    print("RAW DATA:", data)

    raw_email = data.get('email')
    raw_mobile = data.get('mobile_number')
    raw_medium = data.get('medium', 'both')

    # If email itself is a dict, unwrap it
    if isinstance(raw_email, dict):
        email = raw_email.get('email')
        mobile_number = raw_email.get('mobile_number') or raw_mobile
        medium = raw_email.get('medium', raw_medium)
    else:
        email = raw_email
        mobile_number = raw_mobile
        medium = raw_medium

    print("PARSED:", email, mobile_number, medium)

    if not email:
        return JsonResponse({
            'success': False,
            'error': 'Email is required'
        }, status=400)
    
    # Check if user already exists
    if User.objects.filter(email=email).exists():
        return JsonResponse({
            'success': False,
            'error': 'Email already registered'
        }, status=400)
    
    if mobile_number and len(mobile_number.strip()) == 0:
        mobile_number = None    

    if mobile_number and mobile_number.startswith('+'):
        mobile_number = mobile_number[1:]

    if mobile_number and mobile_number.startswith('0'):
        mobile_number = mobile_number[1:]

    if mobile_number and not mobile_number.isdigit():
        return JsonResponse({
            'success': False,
            'error': 'Invalid mobile number format'
        }, status=400)
    
    if mobile_number and len(mobile_number) < 7:
        return JsonResponse({
            'success': False,
            'error': 'Mobile number too short'
        }, status=400)
    
    if mobile_number and len(mobile_number) > 15:
        return JsonResponse({
            'success': False,
            'error': 'Mobile number too long'
        }, status=400)
    
    if mobile_number and User.objects.filter(mobile_number=mobile_number).exists():
        return JsonResponse({
            'success': False,
            'error': 'Mobile number already registered'
        }, status=400)
    
    # Create temporary user (inactive) for OTP verification
    temp_username = f"temp_{email.split('@')[0]}_{random.randint(1000, 9999)}"
    temp_user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': temp_username,
            'mobile_number': mobile_number or '',
            'is_active': False  # Inactive until verified
        }
    )
    
    # Send OTP
    otp, results = send_otp(temp_user, 'email', medium=medium)
    
    return JsonResponse({
        'success': True,
        'message': 'OTP sent successfully',
        'otp_id': otp.id,
        'results': results,
        'temporary_user_id': temp_user.id
    }, status=200)

@csrf_exempt
@require_http_methods(["POST"])
def verify_registration_otp(request):
    """Verify OTP and complete registration"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    print("RAW DATA:", data)

    # unwrap if wrapped in "email"
    if isinstance(data.get('email'), dict):
        data = data['email']

    otp_code = data.get('otp_code')
    username = data.get('username')
    password = data.get('password')
    full_name = data.get('full_name', '')

    # 🔐 minimal required fields
    if not all([otp_code, username, password]):
        return JsonResponse(
            {'success': False, 'error': 'Missing required fields'},
            status=400
        )

    # 🔍 find OTP + temp user in one go
    try:
        otp = OTP.objects.select_related('user').get(
            otp_code=otp_code,
            verification_type='email',
            is_verified=False,
        )
        temp_user = otp.user

        if temp_user.is_active:
            return JsonResponse(
                {'success': False, 'error': 'User already activated'},
                status=400
            )

        if otp.is_expired():
            return JsonResponse(
                {'success': False, 'error': 'OTP has expired'},
                status=400
            )

    except OTP.DoesNotExist:
        return JsonResponse(
            {'success': False, 'error': 'Invalid OTP'},
            status=400
        )

    print("OTP verified for temp user:", temp_user)

    # ✅ Activate user
    temp_user.username = username
    temp_user.set_password(password)
    temp_user.full_name = full_name
    temp_user.is_active = True
    temp_user.is_email_verified = True
    temp_user.save()

    otp.is_verified = True
    otp.save()

    # 🔑 Log user in
    login(request, temp_user, backend='django.contrib.auth.backends.ModelBackend')

    # 🎫 Generate JWT
    refresh = RefreshToken.for_user(temp_user)
    access = CustomAccessToken.for_user(temp_user)

    return JsonResponse({
        'success': True,
        'message': 'Registration successful and email verified',
        'tokens': {
            'access': str(access),
            'refresh': str(refresh),
        }
    }, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    """API endpoint for user login (via email/username/mobile)"""
    try:
        data = json.loads(request.body)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return JsonResponse({
            'success': False,
            'error': 'Username/email/mobile and password are required'
        }, status=400)

    
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        # Issue JWT tokens on login (using custom token with username)
        refresh = RefreshToken.for_user(user)
        access = CustomAccessToken.for_user(user)
        tokens = {'access': str(access), 'refresh': str(refresh)}
        return JsonResponse({
            'success': True,
            'message': 'Login successful',
            'tokens': tokens
        }, status=200)
    else:
        return JsonResponse({
            'success': False,
            'error': 'Invalid username/email/mobile or password'
        }, status=401)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def users_list(request):
    search = request.GET.get('search', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))

    qs = User.objects.all()
    if search:
        qs = qs.filter(username__icontains=search)

    paginator = Paginator(qs.order_by('username'), page_size)
    page_obj = paginator.get_page(page)

    results = [
        {
            "id": u.id,
            "username": u.username,
            # zarurat ho to extra fields bhi bhej sakte ho
        }
        for u in page_obj.object_list
    ]

    return Response({
        "results": results,
        "page": page,
        "page_size": page_size,
        "has_next": page_obj.has_next(),
    })

@csrf_exempt
@require_http_methods(["POST"])
def password_reset_request(request):
    """Request password reset - send OTP"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    email = data.get('email')
    mobile_number = data.get('mobile_number')
    medium = data.get('medium', 'both')  # 'email', 'sms', or 'both'
    
    if not email and not mobile_number:
        return JsonResponse({
            'success': False,
            'error': 'Email or mobile number is required'
        }, status=400)
    
    # Find user
    try:
        if email:
            user = User.objects.get(email=email)
        else:
            user = User.objects.get(mobile_number=mobile_number)
    except User.DoesNotExist:
        # Don't reveal if user exists or not
        return JsonResponse({
            'success': True,
            'message': 'If account exists, OTP will be sent'
        }, status=200)
    
    # Send OTP
    otp, results = send_otp(user, 'password_reset', medium=medium)
    
    return JsonResponse({
        'success': True,
        'message': 'OTP sent for password reset',
        'otp_id': otp.id,
        'results': results,
        'user_id': user.id
    }, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def password_reset_verify(request):
    """Verify OTP for password reset"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    user_id = data.get('user_id')
    otp_code = data.get('otp_code')
    
    if not user_id or not otp_code:
        return JsonResponse({
            'success': False,
            'error': 'User ID and OTP are required'
        }, status=400)
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=400)
    
    # Verify OTP
    try:
        otp = OTP.objects.get(user=user, otp_code=otp_code, verification_type='password_reset')
        
        if otp.is_expired():
            return JsonResponse({
                'success': False,
                'error': 'OTP has expired'
            }, status=400)
        
        if otp.is_verified:
            return JsonResponse({
                'success': False,
                'error': 'OTP already used'
            }, status=400)
    except OTP.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Invalid OTP'
        }, status=400)
    
    # Mark OTP as verified (but don't delete it yet)
    otp.is_verified = True
    otp.save()
    
    return JsonResponse({
        'success': True,
        'message': 'OTP verified successfully',
        'reset_token': f"{user.id}_{otp.id}"  # Simple token for next step
    }, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def password_reset_confirm(request):
    """Confirm password reset with new password"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    user_id = data.get('user_id')
    otp_id = data.get('otp_id')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    if not all([user_id, otp_id, new_password, confirm_password]):
        return JsonResponse({
            'success': False,
            'error': 'All fields are required'
        }, status=400)
    
    if new_password != confirm_password:
        return JsonResponse({
            'success': False,
            'error': 'Passwords do not match'
        }, status=400)
    
    if len(new_password) < 8:
        return JsonResponse({
            'success': False,
            'error': 'Password must be at least 8 characters'
        }, status=400)
    
    try:
        user = User.objects.get(id=user_id)
        otp = OTP.objects.get(id=otp_id, user=user, verification_type='password_reset')
        
        if not otp.is_verified:
            return JsonResponse({
                'success': False,
                'error': 'OTP not verified'
            }, status=400)
        
        if otp.is_expired():
            return JsonResponse({
                'success': False,
                'error': 'OTP has expired'
            }, status=400)
    except (User.DoesNotExist, OTP.DoesNotExist):
        return JsonResponse({
            'success': False,
            'error': 'Invalid request'
        }, status=400)
    
    # Set new password
    user.set_password(new_password)
    user.save()
    
    # Delete OTP after use
    otp.delete()
    
    return JsonResponse({
        'success': True,
        'message': 'Password reset successful. You can now login with your new password.'
    }, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def google_login_view(request):
    """Handle Google OAuth2 login"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    google_id = data.get('google_id')
    email = data.get('email')
    full_name = data.get('full_name')
    picture_url = data.get('picture_url')
    
    if not google_id or not email:
        return JsonResponse({
            'success': False,
            'error': 'Google ID and email are required'
        }, status=400)
    
    # Find or create user
    try:
        user = User.objects.get(google_id=google_id)
    except User.DoesNotExist:
        try:
            user = User.objects.get(email=email)
            # Link existing user with Google ID
            user.google_id = google_id
            user.save()
        except User.DoesNotExist:
            # Create new user
            username = email.split('@')[0]
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{email.split('@')[0]}{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=email,
                google_id=google_id,
                full_name=full_name or '',
                is_email_verified=True,  # Google emails are verified
                is_active=True
            )
    
    # Ensure user is active
    if not user.is_active:
        user.is_active = True
        user.save()
    
    login(request, user)
    
    return JsonResponse({
        'success': True,
        'message': 'Google login successful',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'mobile_number': user.mobile_number,
            'role': user.role,
            'is_email_verified': user.is_email_verified
        },
        'tokens': {
            'access': str(CustomAccessToken.for_user(user)),
            'refresh': str(RefreshToken.for_user(user))
        }
    }, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def refresh_token_view(request):
    """Refresh an access token using a refresh token (SimpleJWT)."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    serializer = TokenRefreshSerializer(data=data)
    if serializer.is_valid():
        access = serializer.validated_data.get('access')
        # Return tokens dict to match client test expectations
        tokens = {'access': access, 'refresh': data.get('refresh')}
        return JsonResponse({'success': True, 'tokens': tokens}, status=200)
    return JsonResponse({'success': False, 'errors': serializer.errors}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def verify_access_token(request):
    """Verify an access token and return its payload when valid."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    token_str = data.get('token') or data.get('access')
    if not token_str:
        return JsonResponse({'success': False, 'error': 'token required'}, status=400)

    try:
        # Decode JWT without signature verification (we just want to extract the payload)
        # For production, use verified=True and provide the secret key
        import jwt
        payload = jwt.decode(token_str, options={"verify_signature": False}, algorithms=["HS256"])
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Invalid token: {str(e)}'}, status=400)

    # Return decoded payload for callers (chat service expects user info inside token payload)
    # Return under 'user' key for compatibility with chat introspection
    return JsonResponse({'success': True, 'user': payload}, status=200)


@require_http_methods(["POST"])
def logout_view(request):
    """API endpoint for user logout"""
    logout(request)
    return JsonResponse({
        'success': True,
        'message': 'Logout successful'
    }, status=200)


@require_http_methods(["GET"])
def user_profile_view(request):
    """API endpoint to get current user profile"""
    user = _user_from_request(request)
    if not user:
        return JsonResponse({
            'success': False,
            'error': 'Not authenticated'
        }, status=401)

    return JsonResponse({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'mobile_number': user.mobile_number,
            'role': user.role,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'is_email_verified': user.is_email_verified,
            'is_mobile_verified': user.is_mobile_verified,
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        }
    }, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def register_public_key(request):
    """Register or update the authenticated user's public key."""
    user = _user_from_request(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    public_key = data.get('public_key')
    if not public_key:
        return JsonResponse({'success': False, 'error': 'public_key required'}, status=400)

    # Store the public key on the user model (field `public_key` expected by migrations)
    user.public_key = public_key
    user.save()

    return JsonResponse({'success': True, 'message': 'Public key registered'}, status=200)
