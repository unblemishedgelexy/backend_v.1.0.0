# Django Advanced Authentication System

A production-ready authentication backend with JWT-like tokens, OTP verification, email/SMS notifications, password reset, user roles, and Google OAuth integration.

## 🚀 Features

✅ **Multi-Channel Authentication**
- Login with username, email, or mobile number
- OTP-based registration and verification
- Email and SMS verification

✅ **Token System**
- Access tokens (15-minute expiry)
- Refresh tokens (7-day expiry)
- Automatic token refresh endpoint
- Base64-encoded JWT-like tokens

✅ **Security**
- Secure password hashing
- CSRF protection
- Input validation
- Email/mobile verification flags
- SQL injection prevention

✅ **User Management**
- 4 User roles: admin, manager, creator, user
- Email verification tracking
- Mobile verification tracking
- User profile management
- Google OAuth integration ready

✅ **Password Management**
- 3-step OTP-based password reset
- Email notifications
- SMS notifications (optional, Twilio)
- Secure password change

---

## 📋 Quick Setup (Windows PowerShell)

### 1. Create Virtual Environment
```powershell
cd c:\Users\hp\Desktop\unknow_app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Configure Environment
Create/edit `.env` file:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Email (Gmail SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# SMS (Twilio) - Optional
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
TWILIO_PHONE_NUMBER=+1234567890

# OTP Settings
OTP_EXPIRY_MINUTES=10
OTP_LENGTH=6

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-secret
```

### 4. Database Setup
```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 5. Run Server
```powershell
python manage.py runserver
```

Server will be at: **http://127.0.0.1:8000/**

---

## 📡 API Endpoints (Complete Reference)

### Base URL
```
http://127.0.0.1:8000/accounts/
```

### 1️⃣ Home
**GET** `/`
```json
Response:
{
  "success": true,
  "message": "Welcome to Django Auth API",
  "authenticated": false,
  "endpoints": {...}
}
```

---

### 2️⃣ Registration with OTP (Recommended)

#### Step 1: Request OTP
**POST** `/register/send-otp/`
```json
Request:
{
  "email": "user@example.com",
  "mobile_number": "9876543210",
  "medium": "both"
}

Response (200):
{
  "success": true,
  "message": "OTP sent successfully",
  "otp_id": 1,
  "temporary_user_id": 5,
  "results": {
    "email": {"success": true, "message": "OTP sent to email successfully"},
    "sms": {"success": false, "message": "Twilio not installed"}
  }
}
```

#### Step 2: Verify OTP & Register
**POST** `/register/verify-otp/`
```json
Request:
{
  "otp_code": "123456",
  "temporary_user_id": 5,
  "username": "newuser",
  "password": "SecurePass@123",
  "full_name": "John Doe"
}

Response (201):
{
  "success": true,
  "message": "Registration successful and email verified",
  "tokens": {
    "access": "eyJ1c2VyX2lkIjogNSwgInVzZXJuYW1lIjogI...",
    "refresh": "eyJ1c2VyX2lkIjogNSwgInR5cGUiOiAi..."
  },
  "user": {
    "id": 5,
    "username": "newuser",
    "email": "user@example.com",
    "full_name": "John Doe",
    "mobile_number": "9876543210",
    "role": "user",
    "is_email_verified": true,
    "is_mobile_verified": false
  }
}
```

---

### 3️⃣ Direct Registration (Without OTP)

**POST** `/register/`
```json
Request:
{
  "username": "testuser",
  "email": "test@example.com",
  "password1": "SecurePass@123",
  "password2": "SecurePass@123",
  "full_name": "Test User",
  "mobile_number": "9876543210"
}

Response (201):
{
  "success": true,
  "tokens": {...},
  "user": {...}
}
```

---

### 4️⃣ Login

**POST** `/login/`
```json
Request:
{
  "username": "newuser",
  "password": "SecurePass@123"
}

Response (200):
{
  "success": true,
  "message": "Login successful",
  "tokens": {
    "access": "eyJ1c2VyX2lkIjogNSwgInVzZXJuYW1lIjog...",
    "refresh": "eyJ1c2VyX2lkIjogNSwgInR5cGUiOiAi..."
  },
  "user": {...}
}
```

**✨ Note**: Can login with:
- Username: `newuser`
- Email: `user@example.com`
- Mobile: `9876543210`

---

### 5️⃣ Token Refresh

**POST** `/token/refresh/`
```json
Request:
{
  "refresh": "eyJ1c2VyX2lkIjogNSwgInR5cGUiOiAi..."
}

Response (200):
{
  "success": true,
  "message": "Token refreshed successfully",
  "tokens": {
    "access": "new-access-token-here",
    "refresh": "new-refresh-token-here"
  }
}
```

**📌 When to use**:
- Access token expired after 15 minutes
- Need fresh token to continue authenticated requests
- Automatically get new refresh token too (7-day expiry)

---

### 6️⃣ Password Reset (3-Step Process)

#### Step 1: Request Password Reset
**POST** `/password-reset/request/`
```json
Request:
{
  "email": "user@example.com",
  "medium": "email"
}

Response (200):
{
  "success": true,
  "message": "OTP sent for password reset",
  "otp_id": 2,
  "user_id": 5,
  "results": {
    "email": {"success": true}
  }
}
```

#### Step 2: Verify OTP
**POST** `/password-reset/verify/`
```json
Request:
{
  "user_id": 5,
  "otp_code": "654321"
}

Response (200):
{
  "success": true,
  "message": "OTP verified successfully",
  "reset_token": "5_2"
}
```

#### Step 3: Confirm Password Reset
**POST** `/password-reset/confirm/`
```json
Request:
{
  "user_id": 5,
  "otp_id": 2,
  "new_password": "NewPass@123",
  "confirm_password": "NewPass@123"
}

Response (200):
{
  "success": true,
  "message": "Password reset successful. Login with new password."
}
```

---

### 7️⃣ Google Login

**POST** `/google-login/`
```json
Request:
{
  "google_id": "1234567890",
  "email": "user@gmail.com",
  "full_name": "Google User",
  "picture_url": "https://..."
}

Response (200):
{
  "success": true,
  "message": "Google login successful",
  "tokens": {...},
  "user": {...}
}
```

---

### 8️⃣ User Profile

**GET** `/me/`

**Headers**:
```
Authorization: Bearer <access-token>
```

**Response (200)**:
```json
{
  "success": true,
  "user": {
    "id": 5,
    "username": "newuser",
    "email": "user@example.com",
    "full_name": "John Doe",
    "mobile_number": "9876543210",
    "role": "user",
    "is_staff": false,
    "is_superuser": false,
    "is_email_verified": true,
    "is_mobile_verified": false,
    "date_joined": "2025-11-29T23:24:45.123456Z",
    "last_login": "2025-11-29T23:25:00.654321Z"
  }
}
```

---

### 9️⃣ Logout

**POST** `/logout/`
```json
Response (200):
{
  "success": true,
  "message": "Logout successful"
}
```

---

## 🔐 Token System Guide

### Access Token
- **Purpose**: Used for authenticated API requests
- **Lifetime**: 15 minutes
- **Format**: Base64 encoded JSON
- **When Expired**: Use refresh token to get new one
- **Usage**: Include in `Authorization: Bearer <token>` header

### Refresh Token
- **Purpose**: Generate new access tokens
- **Lifetime**: 7 days
- **Format**: Base64 encoded JSON with refresh flag
- **When Expired**: User must login again
- **Usage**: POST to `/token/refresh/` endpoint

### Frontend Integration (JavaScript)

```javascript
// After login/register
const { tokens, user } = response;
localStorage.setItem('accessToken', tokens.access);
localStorage.setItem('refreshToken', tokens.refresh);

// Make API request with token
const response = await fetch('http://127.0.0.1:8000/accounts/me/', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
    'Content-Type': 'application/json'
  }
});

// If access token expires (401), refresh it
async function refreshTokens() {
  const response = await fetch('http://127.0.0.1:8000/accounts/token/refresh/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      refresh: localStorage.getItem('refreshToken') 
    })
  });
  
  if (response.ok) {
    const data = await response.json();
    localStorage.setItem('accessToken', data.tokens.access);
    localStorage.setItem('refreshToken', data.tokens.refresh);
    return true;
  }
  // Refresh token expired, redirect to login
  return false;
}
```

---

## 👥 User Roles

| Role | Description | Permissions |
|------|-------------|------------|
| **user** | Regular user | View own profile |
| **creator** | Content creator | Create & manage content |
| **manager** | Team lead | Manage users & content |
| **admin** | Administrator | Full system access |

**Set role in admin panel**: http://127.0.0.1:8000/admin/

---

## 🧪 Testing with cURL

### Test 1: Register with OTP
```bash
# Step 1: Send OTP
curl -X POST http://127.0.0.1:8000/accounts/register/send-otp/ ^
  -H "Content-Type: application/json" ^
  -d "{ \"email\": \"test@example.com\", \"mobile_number\": \"9876543210\", \"medium\": \"email\" }"

# Copy temporary_user_id and check terminal for OTP code

# Step 2: Verify OTP
curl -X POST http://127.0.0.1:8000/accounts/register/verify-otp/ ^
  -H "Content-Type: application/json" ^
  -d "{ \"otp_code\": \"123456\", \"temporary_user_id\": 1, \"username\": \"testuser\", \"password\": \"SecurePass@123\", \"full_name\": \"Test User\" }"
```

### Test 2: Login
```bash
curl -X POST http://127.0.0.1:8000/accounts/login/ ^
  -H "Content-Type: application/json" ^
  -d "{ \"username\": \"testuser\", \"password\": \"SecurePass@123\" }"
```

### Test 3: Get Profile
```bash
curl -X GET http://127.0.0.1:8000/accounts/me/ ^
  -H "Authorization: Bearer <your-access-token>"
```

### Test 4: Refresh Token
```bash
curl -X POST http://127.0.0.1:8000/accounts/token/refresh/ ^
  -H "Content-Type: application/json" ^
  -d "{ \"refresh\": \"<your-refresh-token>\" }"
```

---

## ⚙️ Configuration Guide

### Email Setup (Gmail)

1. Enable 2FA on Gmail
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Add to `.env`:
```env
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password
```

### SMS Setup (Twilio - Optional)

1. Create Twilio account: https://www.twilio.com/
2. Get credentials from Twilio Dashboard
3. Add to `.env`:
```env
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
TWILIO_PHONE_NUMBER=+1234567890
```

### Google OAuth Setup

1. Create project: https://console.cloud.google.com/
2. Create OAuth 2.0 credentials (Desktop Application)
3. Add to `.env`:
```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret
```

---

## 📁 Project Structure

```
unknow_app/
├── manage.py
├── .env (secrets - not in repo)
├── requirements.txt
├── README.md (this file)
│
├── auth_project/
│   ├── settings.py (Django configuration)
│   ├── urls.py (root URL routes)
│   ├── wsgi.py
│   └── asgi.py
│
└── accounts/
    ├── models.py (User & OTP models)
    ├── views.py (API endpoints)
    ├── urls.py (accounts routes)
    ├── backends.py (email/username/mobile auth backend)
    ├── utils.py (send OTP functions)
    ├── forms.py (registration/login forms)
    ├── admin.py (admin panel configuration)
    └── migrations/
        ├── 0001_initial.py
        └── 0002_user_fields_and_otp.py
```

---

## 🐛 Troubleshooting

### OTP Not Sending?
```bash
# Check .env email configuration
# In development, OTPs print to console output
# Check your Django server terminal
```

### SMS Not Sending?
```bash
# Install twilio: pip install twilio
# Add valid credentials to .env
# Or set EMAIL_BACKEND for console output in development
```

### Token Invalid?
```bash
# Check token expiry (access: 15 min, refresh: 7 days)
# Make sure Bearer prefix is included
# Example: Authorization: Bearer eyJ1c2VyX2lkIjog...
```

### Database Errors?
```powershell
# Reset database:
rm db.sqlite3
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

---

## 📚 Admin Panel

**URL**: http://127.0.0.1:8000/admin/

**Features**:
- Manage users and assign roles
- View OTP history
- Mark emails/mobiles as verified
- Set user as staff/superuser

---

## 🔒 Security Best Practices

1. ✅ Never commit `.env` (added to `.gitignore`)
2. ✅ Use strong passwords (min 8 chars)
3. ✅ Change `SECRET_KEY` in production
4. ✅ Set `DEBUG = False` in production
5. ✅ Use HTTPS in production
6. ✅ Store tokens securely (not in localStorage for sensitive apps)
7. ✅ Validate all inputs server-side
8. ✅ Use CORS properly for your frontend domain

---

## 🚀 Production Deployment

### Pre-Deployment Checklist
- [ ] Generate new `SECRET_KEY`
- [ ] Set `DEBUG = False`
- [ ] Use PostgreSQL instead of SQLite
- [ ] Configure real email service (SendGrid, AWS SES)
- [ ] Configure real SMS service (Twilio)
- [ ] Setup proper logging
- [ ] Add rate limiting to endpoints
- [ ] Configure HTTPS
- [ ] Setup monitoring/alerting
- [ ] Test all endpoints
- [ ] Backup database regularly

### Deployment Options
- **Heroku** (simple, good for startups)
- **AWS EC2** (scalable, more control)
- **DigitalOcean** (affordable, easy)
- **PythonAnywhere** (Python-specific)

---

## 📝 Notes

- All responses follow `{success, message, data}` JSON format
- All timestamps are in UTC timezone
- OTP codes are 6 digits by default (configurable in `.env`)
- OTP expires after 10 minutes by default (configurable)
- Mobile numbers should include country code (e.g., +91 for India)

---

**Version**: 2.0.0 (Updated with comprehensive token documentation)  
**Last Updated**: November 29, 2025  
**License**: MIT
