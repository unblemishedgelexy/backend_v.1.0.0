# Frontend Integration Guide

Quick reference for frontend developers integrating with this Django authentication backend.

## 🎯 Quick Start (5 Minutes)

### 1. Register User with OTP

```javascript
// Step 1: Send OTP
const sendOTP = async (email) => {
  const response = await fetch('http://127.0.0.1:8000/accounts/register/send-otp/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email: email,
      mobile_number: '9876543210',
      medium: 'email'
    })
  });
  const data = await response.json();
  return data.temporary_user_id; // Save this
};

// Step 2: Verify OTP & Register
const registerWithOTP = async (tempUserId, otp, username, password) => {
  const response = await fetch('http://127.0.0.1:8000/accounts/register/verify-otp/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      otp_code: otp,
      temporary_user_id: tempUserId,
      username: username,
      password: password,
      full_name: 'User Name'
    })
  });
  const data = await response.json();
  if (data.success) {
    localStorage.setItem('accessToken', data.tokens.access);
    localStorage.setItem('refreshToken', data.tokens.refresh);
    return data.user;
  }
  throw new Error(data.error);
};
```

### 2. Login User

```javascript
const login = async (username, password) => {
  const response = await fetch('http://127.0.0.1:8000/accounts/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: username,  // Can also use email or mobile
      password: password
    })
  });
  const data = await response.json();
  if (data.success) {
    localStorage.setItem('accessToken', data.tokens.access);
    localStorage.setItem('refreshToken', data.tokens.refresh);
    return data.user;
  }
  throw new Error(data.error);
};
```

### 3. Make Authenticated Requests

```javascript
const getProfile = async () => {
  const token = localStorage.getItem('accessToken');
  const response = await fetch('http://127.0.0.1:8000/accounts/me/', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  const data = await response.json();
  return data.user;
};

// Or use this reusable function
const apiCall = async (endpoint, method = 'GET', body = null) => {
  const token = localStorage.getItem('accessToken');
  const options = {
    method,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  };
  if (body) options.body = JSON.stringify(body);
  
  const response = await fetch(`http://127.0.0.1:8000${endpoint}`, options);
  const data = await response.json();
  
  // If token expired, refresh it
  if (response.status === 401 && data.error?.includes('token')) {
    await refreshAccessToken();
    return apiCall(endpoint, method, body); // Retry
  }
  
  return data;
};
```

### 4. Refresh Token (Auto-Call When Expired)

```javascript
const refreshAccessToken = async () => {
  const refreshToken = localStorage.getItem('refreshToken');
  const response = await fetch('http://127.0.0.1:8000/accounts/token/refresh/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: refreshToken })
  });
  const data = await response.json();
  if (data.success) {
    localStorage.setItem('accessToken', data.tokens.access);
    localStorage.setItem('refreshToken', data.tokens.refresh);
    return true;
  }
  // Redirect to login
  localStorage.clear();
  window.location.href = '/login';
  return false;
};
```

### 5. Logout

```javascript
const logout = () => {
  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
  window.location.href = '/login';
};
```

---

## 🔑 Token Management

### Token Structure

**Access Token** (Base64 encoded):
```json
{
  "user_id": 5,
  "username": "john",
  "email": "john@example.com",
  "iat": 1732824600,
  "exp": 1732825500
}
```

**Refresh Token** (Base64 encoded):
```json
{
  "user_id": 5,
  "type": "refresh",
  "iat": 1732824600,
  "exp": 1735503000
}
```

### Token Lifetimes
- Access Token: **15 minutes** (900 seconds)
- Refresh Token: **7 days** (604,800 seconds)

### Handle Token Expiration

```javascript
class AuthService {
  static isTokenExpired(token) {
    try {
      const decoded = JSON.parse(atob(token));
      return Date.now() / 1000 > decoded.exp;
    } catch {
      return true;
    }
  }

  static getTokenExpiryTime(token) {
    try {
      const decoded = JSON.parse(atob(token));
      const secondsRemaining = decoded.exp - (Date.now() / 1000);
      return Math.max(0, secondsRemaining);
    } catch {
      return 0;
    }
  }

  static scheduleTokenRefresh() {
    const token = localStorage.getItem('accessToken');
    const secondsRemaining = this.getTokenExpiryTime(token);
    const millisecondsRemaining = (secondsRemaining - 60) * 1000; // Refresh 1 min before expiry
    
    if (millisecondsRemaining > 0) {
      setTimeout(() => {
        refreshAccessToken();
      }, millisecondsRemaining);
    }
  }
}

// Call after login
AuthService.scheduleTokenRefresh();
```

---

## 📱 Complete Example: React Integration

```jsx
import React, { useState, useEffect } from 'react';

const AuthContext = React.createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);

  const login = async (username, password) => {
    setLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/accounts/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await response.json();
      
      if (data.success) {
        localStorage.setItem('accessToken', data.tokens.access);
        localStorage.setItem('refreshToken', data.tokens.refresh);
        setUser(data.user);
        return data.user;
      }
      throw new Error(data.error);
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    setUser(null);
  };

  const apiCall = async (endpoint, method = 'GET', body = null) => {
    let token = localStorage.getItem('accessToken');
    
    const options = {
      method,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    };
    if (body) options.body = JSON.stringify(body);

    let response = await fetch(`http://127.0.0.1:8000${endpoint}`, options);
    let data = await response.json();

    // If token expired, refresh and retry
    if (response.status === 401) {
      const refreshToken = localStorage.getItem('refreshToken');
      const refreshResponse = await fetch('http://127.0.0.1:8000/accounts/token/refresh/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken })
      });
      const refreshData = await refreshResponse.json();

      if (refreshData.success) {
        token = refreshData.tokens.access;
        localStorage.setItem('accessToken', token);
        localStorage.setItem('refreshToken', refreshData.tokens.refresh);

        // Retry original request
        options.headers['Authorization'] = `Bearer ${token}`;
        response = await fetch(`http://127.0.0.1:8000${endpoint}`, options);
        data = await response.json();
      } else {
        logout();
        throw new Error('Session expired');
      }
    }

    return data;
  };

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('accessToken');
    if (token) {
      apiCall('/accounts/me/').then(data => {
        if (data.success) setUser(data.user);
      }).catch(() => logout());
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout, apiCall, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => React.useContext(AuthContext);
```

---

## 🌐 API Endpoints Reference

### Authentication
```
POST   /accounts/register/              - Direct registration
POST   /accounts/register/send-otp/     - Send registration OTP
POST   /accounts/register/verify-otp/   - Verify OTP & register
POST   /accounts/login/                 - User login
POST   /accounts/logout/                - User logout
GET    /accounts/me/                    - Get user profile
POST   /accounts/token/refresh/         - Refresh access token
```

### Password Management
```
POST   /accounts/password-reset/request/   - Request password reset
POST   /accounts/password-reset/verify/    - Verify reset OTP
POST   /accounts/password-reset/confirm/   - Confirm new password
```

### Social Login
```
POST   /accounts/google-login/          - Google OAuth login
```

---

## ⚠️ Error Handling

### Common Errors

```javascript
const handleAPIError = (error) => {
  if (error.error?.includes('already exists')) {
    return 'Email or username already registered';
  }
  if (error.error?.includes('Invalid')) {
    return 'Invalid username, email, or password';
  }
  if (error.error?.includes('expired')) {
    return 'Session expired. Please login again';
  }
  if (error.error?.includes('Invalid JSON')) {
    return 'Invalid request format';
  }
  return error.error || 'Unknown error occurred';
};
```

### Response Status Codes

```javascript
// 200: Success
// 201: Created (new user registered)
// 400: Bad Request (invalid data)
// 401: Unauthorized (invalid token)
// 404: Not Found (user not found)
// 500: Server Error
```

---

## 🔒 Security Tips

1. **Store tokens safely**
   ```javascript
   // ✅ GOOD: Store in memory or secure cookie
   sessionStorage.setItem('token', token);
   
   // ⚠️ RISKY: localStorage can be accessed by XSS
   localStorage.setItem('token', token);
   ```

2. **Always use HTTPS in production**
   ```javascript
   const API_URL = process.env.REACT_APP_API_URL;
   // Should be https://your-domain.com/accounts/
   ```

3. **Never expose tokens in URLs**
   ```javascript
   // ❌ DON'T DO THIS
   fetch(`http://127.0.0.1:8000/api?token=${accessToken}`);
   
   // ✅ DO THIS
   fetch('http://127.0.0.1:8000/api', {
     headers: { 'Authorization': `Bearer ${accessToken}` }
   });
   ```

4. **Implement CSRF protection**
   ```javascript
   // For POST requests, include CSRF token from cookies
   fetch('http://127.0.0.1:8000/accounts/login/', {
     method: 'POST',
     headers: {
       'X-CSRFToken': getCookie('csrftoken'),
       'Content-Type': 'application/json'
     },
     body: JSON.stringify(data)
   });
   ```

---

## 📊 User Object Structure

```javascript
{
  id: 5,
  username: "john_doe",
  email: "john@example.com",
  full_name: "John Doe",
  mobile_number: "9876543210",
  role: "user",  // or "creator", "manager", "admin"
  is_staff: false,
  is_superuser: false,
  is_email_verified: true,
  is_mobile_verified: false,
  date_joined: "2025-11-29T23:24:45.123456Z",
  last_login: "2025-11-29T23:25:00.654321Z"
}
```

---

## 🚀 Deployment Configuration

### Development
```env
API_URL=http://127.0.0.1:8000
DEBUG=true
```

### Production
```env
API_URL=https://api.yourdomain.com
DEBUG=false
```

---

## 📚 Additional Resources

- Full API Documentation: See `README.md`
- Implementation Details: See `IMPLEMENTATION_SUMMARY.md`
- Django Docs: https://docs.djangoproject.com/
- JWT Concepts: https://jwt.io/

---

**Version**: 1.0.0  
**Last Updated**: November 29, 2025
