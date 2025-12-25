import random
from common.redis_client import redis_client
from common.security import hash_value  

OTP_TTL = 300  # 5 minutes

def generate_otp(email):
    otp = str(random.randint(100000, 999999))
    redis_client.setex(f"otp:register:{email}", OTP_TTL, otp)
    return otp

def verify_otp(key: str, user_otp: str):
    stored = redis_client.get(key)
    if not stored:
        return False, "OTP expired"

    if stored != hash_value(user_otp):
        return False, "Invalid OTP"

    redis_client.delete(key)
    return True, "OTP verified"