from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
import json
from .models import OTP
from .utils import send_otp
from rest_framework_simplejwt.serializers import TokenRefreshSerializer, TokenVerifySerializer
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from .tokens import CustomAccessToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.paginator import Paginator
from common.otp_service import verify_otp
from accounts.tasks import send_registration_otp_email
from common.redis_service import rate_limit, increment_counter


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
def send_registration_otp(request):
    data = json.loads(request.body)

    email = data.get("email")
    username = data.get("username")
    mobile = data.get("mobile_number")

    if not all([email, username, mobile]):
        return JsonResponse(
            {"success": False, "error": "email, username, mobile required"},
            status=400
        )

    # 🔒 Rate limit per email
    if not rate_limit(f"rate:otp:{email}", limit=5, window=3600):
        return JsonResponse(
            {"success": False, "error": "Too many OTP requests"},
            status=429
        )

    # 🔒 Rate limit per IP
    ip = request.META.get("REMOTE_ADDR")
    if not rate_limit(f"rate:otp:ip:{ip}", limit=20, window=3600):
        return JsonResponse(
            {"success": False, "error": "Too many requests"},
            status=429
        )

    if User.objects.filter(username=username).exists():
        return JsonResponse({"success": False, "error": "Username already taken"}, status=400)

    if User.objects.filter(mobile_number=mobile).exists():
        return JsonResponse({"success": False, "error": "Mobile already registered"}, status=400)

    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "username": username,
            "mobile_number": mobile,
            "is_active": False,
        }
    )

    if not created and user.is_active:
        return JsonResponse({"success": False, "error": "Email already registered"}, status=400)

    # 🔥 OTP generation + TTL happens INSIDE WORKER
    send_registration_otp_email.delay(email)


    return JsonResponse({"success": True, "message": "OTP sent"})

@csrf_exempt
def verify_registration_otp(request):
    data = json.loads(request.body)

    email = data.get("email")
    otp = data.get("otp")
    password = data.get("password")

    if not all([email, otp, password]):
        return JsonResponse(
            {"success": False, "error": "email, otp, password required"},
            status=400
        )

    # 🔒 OTP attempt limit
    allowed, _ = increment_counter(f"otp:attempt:{email}", limit=5)
    if not allowed:
        return JsonResponse(
            {"success": False, "error": "Too many wrong attempts"},
            status=429
        )

    # ✅ CORRECT KEY USAGE
    ok, msg = verify_otp(f"otp:register:{email}", otp)
    if not ok:
        return JsonResponse({"success": False, "error": msg}, status=400)

    user = User.objects.get(email=email)

    user.set_password(password)
    user.is_active = True
    user.is_email_verified = True
    user.save()

    return JsonResponse({
        "success": True,
        "message": "Account created successfully"
    })

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
        tokens = {'accessToken': str(access), 'refreshToken': str(refresh)}
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


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user
    data = request.data

    # username change limit (3/day)
    from common.redis_service import increment_counter
    if "username" in data:
        key = f"username_change:{user.id}"
        if not increment_counter(key, 3):
            return Response({"error": "username change limit reached"}, status=429)

        if User.objects.filter(username=data["username"]).exists():
            return Response({"error": "username taken"}, status=400)

        user.username = data["username"]

    if "full_name" in data:
        user.full_name = data["full_name"]

    user.save()
    return Response({"success": True})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_mobile(request):
    mobile = request.data.get("mobile_number")
    user = request.user

    user.mobile_number = mobile
    user.is_mobile_verified = False
    user.save()

    from accounts.redis_otp import send_otp_redis
    otp = send_otp_redis(user.id, "mobile")
    send_otp(user, "sms", otp)

    return Response({"success": True, "message": "OTP sent"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_mobile(request):
    otp = request.data.get("otp")
    user = request.user

    from accounts.redis_otp import verify_otp_redis
    if not verify_otp_redis(user.id, "mobile", otp):
        return Response({"error": "invalid otp"}, status=400)

    user.is_mobile_verified = True
    user.save()
    return Response({"success": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_profile_picture(request):
    image = request.FILES.get("image")
    user = request.user

    from common.imagekit_service import upload_image
    url = upload_image(image, folder="profiles")

    user.profile_image = url
    user.save()

    return Response({"success": True, "url": url})



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
    data = json.loads(request.body)
    email = data.get("email")

    if not email:
        return JsonResponse({"success": False, "error": "email required"}, status=400)

    # rate limit (5 req / 10 min)
    from common.redis_service import rate_limit
    key = f"rate:password_reset:{email}"
    if not rate_limit(key, limit=5, window=600):
        return JsonResponse(
            {"success": False, "error": "Too many requests, try later"},
            status=429
        )

    user = User.objects.filter(email=email).first()
    if not user:
        # security: same response
        return JsonResponse({"success": True, "message": "If account exists, OTP sent"})

    from accounts.redis_otp import send_otp_redis
    otp = send_otp_redis(user.id, "password_reset")

    send_otp(user, "password_reset", otp)  # email/sms util

    return JsonResponse({
        "success": True,
        "message": "OTP sent for password reset"
    })

@csrf_exempt
@require_http_methods(["POST"])
def password_reset_verify(request):
    data = json.loads(request.body)
    email = data.get("email")
    otp = data.get("otp")

    if not email or not otp:
        return JsonResponse(
            {"success": False, "error": "email & otp required"},
            status=400
        )

    user = User.objects.filter(email=email).first()
    if not user:
        return JsonResponse({"success": False, "error": "Invalid OTP"}, status=400)

    from accounts.redis_otp import verify_otp_redis
    if not verify_otp_redis(user.id, "password_reset", otp):
        return JsonResponse({"success": False, "error": "Invalid or expired OTP"}, status=400)

    # generate reset token
    import secrets
    reset_token = secrets.token_urlsafe(32)

    from common.redis_service import set_otp
    set_otp(f"reset_token:{user.id}", reset_token, ttl=600)  # 10 min

    return JsonResponse({
        "success": True,
        "reset_token": reset_token
    })

@csrf_exempt
@require_http_methods(["POST"])
def password_reset_confirm(request):
    data = json.loads(request.body)
    email = data.get("email")
    reset_token = data.get("reset_token")
    new_password = data.get("new_password")

    if not all([email, reset_token, new_password]):
        return JsonResponse(
            {"success": False, "error": "All fields required"},
            status=400
        )

    if len(new_password) < 8:
        return JsonResponse(
            {"success": False, "error": "Password too short"},
            status=400
        )

    user = User.objects.filter(email=email).first()
    if not user:
        return JsonResponse({"success": False, "error": "Invalid token"}, status=400)

    from common.redis_service import get_otp, delete_otp
    stored_token = get_otp(f"reset_token:{user.id}")

    if not stored_token or stored_token != reset_token:
        return JsonResponse(
            {"success": False, "error": "Invalid or expired reset token"},
            status=400
        )

    # set new password
    user.set_password(new_password)
    user.save()

    # cleanup
    delete_otp(f"reset_token:{user.id}")

    return JsonResponse({
        "success": True,
        "message": "Password reset successful"
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_email(request):
    new_email = request.data.get("email")
    user = request.user

    if not new_email:
        return Response({"error": "email required"}, status=400)

    if User.objects.filter(email=new_email).exists():
        return Response({"error": "email already used"}, status=400)

    from accounts.redis_otp import send_otp_redis
    otp = send_otp_redis(user.id, "email_change")

    send_otp(user, "email", otp, to=new_email)

    # temp store email in redis
    from common.redis_service import set_otp
    set_otp(f"pending_email:{user.id}", new_email, 600)

    return Response({"success": True, "message": "OTP sent to new email"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_email_change(request):
    otp = request.data.get("otp")
    user = request.user

    from accounts.redis_otp import verify_otp_redis
    if not verify_otp_redis(user.id, "email_change", otp):
        return Response({"error": "Invalid OTP"}, status=400)

    from common.redis_service import get_otp, delete_otp
    new_email = get_otp(f"pending_email:{user.id}")

    if not new_email:
        return Response({"error": "Email expired"}, status=400)

    user.email = new_email
    user.is_email_verified = True
    user.save()

    delete_otp(f"pending_email:{user.id}")

    return Response({"success": True})

@api_view(["GET"])
def check_username(request):
    username = request.GET.get("username")
    if not username:
        return Response({"error": "username required"}, status=400)

    exists = User.objects.filter(username=username).exists()
    return Response({"available": not exists})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def deactivate_account(request):
    user = request.user
    user.is_active = False
    user.save()
    return Response({"success": True, "message": "Account deactivated"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def security_info(request):
    user = request.user
    return Response({
        "email_verified": user.is_email_verified,
        "mobile_verified": user.is_mobile_verified,
        "last_login": user.last_login,
        "role": user.role,
    })



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
