import random
from common.redis_service import set_otp, get_otp, delete_otp

OTP_TTL = 300  # 5 min

def generate_otp():
    return ''.join(str(random.randint(0, 9)) for _ in range(6))

def send_otp_redis(user_id, purpose):
    otp = generate_otp()
    key = f"otp:{purpose}:{user_id}"
    set_otp(key, otp, OTP_TTL)
    return otp  # email/sms sending yahin se hook karega

def verify_otp_redis(user_id, purpose, otp):
    key = f"otp:{purpose}:{user_id}"
    stored = get_otp(key)
    if not stored or stored != otp:
        return False
    delete_otp(key)
    return True
