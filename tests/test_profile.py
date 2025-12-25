import requests
import json
import time

base = 'http://127.0.0.1:8000'
ts = int(time.time())

# Register new user with unique email/mobile
reg_data = {
    'username': f'testuser{ts}',
    'email': f'test{ts}@example.com',
    'password1': 'TestPass@123',
    'password2': 'TestPass@123',
    'full_name': 'Test User',
    'mobile_number': f'+1{ts%10000000:07d}'
}

print('1. REGISTER')
r = requests.post(f'{base}/accounts/register/', json=reg_data)
print(f'Status: {r.status_code}')
data = r.json()
print(f'Success: {data.get("success")}')

if data.get('success'):
    token = data['tokens']['access']
    print(f'Token (first 50 chars): {token[:50]}...')
    
    # Verify token format
    import base64
    try:
        decoded = base64.b64decode(token).decode()
        payload = json.loads(decoded)
        print(f'Token payload: {json.dumps(payload, indent=2)}')
    except Exception as e:
        print(f'Token decode error: {e}')
    
    print('\n2. GET PROFILE WITH TOKEN')
    headers = {'Authorization': f'Bearer {token}'}
    r = requests.get(f'{base}/accounts/me/', headers=headers)
    print(f'Status: {r.status_code}')
    print(f'Response: {r.text[:500]}')
else:
    print(f'Errors: {data.get("errors")}')
