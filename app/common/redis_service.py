import json
import time
from django.conf import settings
from redis import Redis

redis_client = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True
)

# ---------- OTP ----------
def set_otp(key: str, otp: str, ttl: int):
    redis_client.setex(key, ttl, otp)
    redis_client.setex(f"{key}:created", ttl, int(time.time()))

def get_otp(key: str):
    return redis_client.get(key)

def delete_otp(key: str):
    redis_client.delete(key)

def verify_otp(key: str, user_otp: str):
    stored = redis_client.get(key)
    if not stored:
        return False, "OTP expired"

    if stored != str(user_otp):
        return False, "Invalid OTP"

    redis_client.delete(key)
    return True, "OTP verified"


# ---------- RATE LIMIT ----------
def rate_limit(key: str, limit: int, window: int) -> bool:
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, window)

    if count > limit:
        return False
    return True

# ---------- COUNTER ----------
def increment_counter(key: str, limit: int):
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, 86400)
    return count <= limit, count
