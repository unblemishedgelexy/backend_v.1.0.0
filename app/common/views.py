import time
import hmac
import hashlib
import base64
import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.http import JsonResponse
from dotenv import load_dotenv

load_dotenv()

@api_view(["GET"])
@permission_classes([AllowAny])
def imagekit_auth(request):
    token = base64.urlsafe_b64encode(os.urandom(32)).decode()
    expire = int(time.time()) + 60  # 1 min validity

    signature = hmac.new(
        key=os.getenv("IMAGEKIT_PRIVATE_KEY").encode(),
        msg=f"{token}{expire}".encode(),
        digestmod=hashlib.sha1
    ).hexdigest()

    return JsonResponse({
        "token": token,
        "expire": expire,
        "signature": signature,
        "publicKey": os.getenv("IMAGEKIT_PUBLIC_KEY")
    })
