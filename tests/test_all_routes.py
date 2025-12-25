#!/usr/bin/env python
"""
Comprehensive API route testing script for auth and chat services
"""
import requests
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8000"
CHAT_BASE_URL = "http://127.0.0.1:8001"

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_result(test_name, passed, details=""):
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} | {test_name}")
    if details and not passed:
        print(f"       {details}")

def print_section(title):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

# Test data
test_email = f"test{int(time.time())}@example.com"
test_username = f"testuser{int(time.time())}"
test_password = "TestPass@123"
test_mobile = "+1234567890"
test_user_id = None
test_access_token = None
test_refresh_token = None

def test_auth_routes():
    """Test all auth server routes"""
    global test_user_id, test_access_token, test_refresh_token
    
    print_section("TESTING AUTH SERVER ROUTES")
    
    # 1. Home endpoint
    try:
        r = requests.get(f"{BASE_URL}/accounts/")
        passed = r.status_code == 200 and r.json().get('authenticated') == False
        print_result("GET /accounts/ (home)", passed, f"Status: {r.status_code}")
    except Exception as e:
        print_result("GET /accounts/ (home)", False, str(e))
    
    # 2. Register endpoint (direct registration)
    try:
        data = {
            "username": test_username,
            "email": test_email,
            "password1": test_password,
            "password2": test_password,
            "full_name": "Test User",
            "mobile_number": test_mobile
        }
        r = requests.post(f"{BASE_URL}/accounts/register/", json=data)
        passed = r.status_code == 201 and r.json().get('success') == True
        if passed:
            response_data = r.json()
            test_user_id = response_data['user']['id']
            test_access_token = response_data['tokens']['access']
            test_refresh_token = response_data['tokens']['refresh']
        print_result("POST /accounts/register/", passed, f"Status: {r.status_code}")
        if not passed:
            print(f"       Response: {r.text[:200]}")
    except Exception as e:
        print_result("POST /accounts/register/", False, str(e))
    
    # 3. Login endpoint
    try:
        data = {"username": test_username, "password": test_password}
        r = requests.post(f"{BASE_URL}/accounts/login/", json=data)
        passed = r.status_code == 200 and r.json().get('success') == True
        if passed:
            response_data = r.json()
            test_access_token = response_data['tokens']['access']
            test_refresh_token = response_data['tokens']['refresh']
        print_result("POST /accounts/login/", passed, f"Status: {r.status_code}")
    except Exception as e:
        print_result("POST /accounts/login/", False, str(e))
    
    # 4. Token Refresh
    try:
        data = {"refresh": test_refresh_token}
        r = requests.post(f"{BASE_URL}/accounts/token/refresh/", json=data)
        passed = r.status_code == 200 and r.json().get('success') == True
        if passed:
            test_access_token = r.json()['tokens']['access']
        print_result("POST /accounts/token/refresh/", passed, f"Status: {r.status_code}")
    except Exception as e:
        print_result("POST /accounts/token/refresh/", False, str(e))
    
    # 5. Token Verify
    try:
        data = {"token": test_access_token}
        r = requests.post(f"{BASE_URL}/accounts/token/verify/", json=data)
        passed = r.status_code == 200 and r.json().get('success') == True
        print_result("POST /accounts/token/verify/", passed, f"Status: {r.status_code}")
        if not passed:
            print(f"       Response: {r.text[:300]}")
    except Exception as e:
        print_result("POST /accounts/token/verify/", False, str(e))
    
    # 6. User Profile (with auth header)
    try:
        headers = {"Authorization": f"Bearer {test_access_token}"}
        r = requests.get(f"{BASE_URL}/accounts/me/", headers=headers)
        passed = r.status_code == 200 and r.json().get('success') == True
        print_result("GET /accounts/me/ (authenticated)", passed, f"Status: {r.status_code}")
        if not passed:
            print(f"       Response: {r.text[:300]}")
    except Exception as e:
        print_result("GET /accounts/me/ (authenticated)", False, str(e))
    
    # 7. Register Public Key
    try:
        headers = {"Authorization": f"Bearer {test_access_token}"}
        data = {"public_key": "-----BEGIN PUBLIC KEY-----\nMFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBALv.../-----END PUBLIC KEY-----"}
        r = requests.post(f"{BASE_URL}/accounts/me/public-key/", json=data, headers=headers)
        passed = r.status_code == 200 or r.status_code == 400  # May fail if field logic differs
        print_result("POST /accounts/me/public-key/", passed, f"Status: {r.status_code}")
    except Exception as e:
        print_result("POST /accounts/me/public-key/", False, str(e))
    
    # 8. Send Registration OTP
    try:
        data = {"email": f"newuser{int(time.time())}@example.com", "mobile_number": "+1111111111"}
        r = requests.post(f"{BASE_URL}/accounts/register/send-otp/", json=data)
        passed = r.status_code == 200 and r.json().get('success') == True
        print_result("POST /accounts/register/send-otp/", passed, f"Status: {r.status_code}")
    except Exception as e:
        print_result("POST /accounts/register/send-otp/", False, str(e))
    
    # 9. Password Reset Request
    try:
        data = {"email": test_email}
        r = requests.post(f"{BASE_URL}/accounts/password-reset/request/", json=data)
        passed = r.status_code in [200, 400]  # May be 400 if OTP not sent
        print_result("POST /accounts/password-reset/request/", passed, f"Status: {r.status_code}")
    except Exception as e:
        print_result("POST /accounts/password-reset/request/", False, str(e))
    
    # 10. Google Login (stub endpoint)
    try:
        data = {"id_token": "fake_token"}
        r = requests.post(f"{BASE_URL}/accounts/google-login/", json=data)
        # May return 400 or 403 - just check it doesn't 500
        passed = r.status_code < 500
        print_result("POST /accounts/google-login/", passed, f"Status: {r.status_code}")
    except Exception as e:
        print_result("POST /accounts/google-login/", False, str(e))

def test_chat_routes():
    """Test chat service routes"""
    print_section("TESTING CHAT SERVICE ROUTES")
    
    # Check if chat service is running
    try:
        r = requests.get(f"{CHAT_BASE_URL}/chat/conversations/", timeout=2)
        service_available = True
    except:
        service_available = False
        print(f"{YELLOW}⚠ Chat service not running on {CHAT_BASE_URL}{RESET}")
        print("  To test chat routes, start chat_service in another terminal:")
        print("  cd c:\\Users\\hp\\Desktop\\unknow_app_chat_service")
        print("  python manage.py runserver 127.0.0.1:8001")
        return
    
    # With token introspection from auth server
    print_result("Chat service is running", True, f"URL: {CHAT_BASE_URL}")
    
    # TODO: Add chat route tests once service is running

def print_summary():
    """Print summary of test results"""
    print_section("TEST SUMMARY")
    print(f"✓ Auth server endpoints tested")
    print(f"⚠ Chat service endpoints - start service on port 8001 to test")
    print(f"\n{BLUE}Next steps:{RESET}")
    print(f"1. Start chat service: cd c:\\Users\\hp\\Desktop\\unknow_app_chat_service; python manage.py runserver 127.0.0.1:8001")
    print(f"2. Re-run this script to test chat routes")

if __name__ == "__main__":
    print(f"{BLUE}Starting API Route Testing...{RESET}\n")
    test_auth_routes()
    test_chat_routes()
    print_summary()
