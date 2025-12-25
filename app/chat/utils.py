import os
import requests
from requests.exceptions import RequestException

AUTH_VERIFY_URL = os.getenv('AUTH_SERVER_VERIFY', 'http://127.0.0.1:8000/accounts/token/verify/')


def verify_token(token: str, timeout: int = 5) -> dict:
    """Verify an access token with the Auth service.

    Returns a dict with keys:
      - success: bool
      - data: parsed response payload when success
      - error: error string when not success

    This function is synchronous and intended for server-side token introspection.
    """
    if not token:
        return {"success": False, "error": "no token provided"}

    try:
        resp = requests.post(AUTH_VERIFY_URL, json={"token": token}, timeout=timeout)
    except RequestException as e:
        return {"success": False, "error": f"request error: {e}"}

    try:
        payload = resp.json()
    except ValueError:
        return {"success": False, "error": f"invalid json response: {resp.text[:200]}"}

    if resp.status_code == 200 and payload.get('success'):
        return {"success": True, "data": payload}

    return {"success": False, "error": payload}
