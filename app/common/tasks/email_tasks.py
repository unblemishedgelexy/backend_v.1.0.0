from celery import shared_task
from django.core.mail import send_mail
from common.redis_client import redis_client
from common.security import hash_value
import random

OTP_TTL = 300  # 5 minutes

@shared_task(
    bind=True,
    name="accounts.send_registration_otp_email",  # 👈 NEW UNIQUE NAME
    autoretry_for=(Exception,),
    retry_backoff=5,
    retry_kwargs={"max_retries": 3},
)
def send_registration_otp_email(self, email: str):
    otp_key = f"otp:register:{email}"

    if redis_client.exists(otp_key):
        return  # prevent spam / resend storm

    otp = str(random.randint(100000, 999999))
    hashed = hash_value(otp)

    redis_client.setex(otp_key, OTP_TTL, hashed)

    send_mail(
        subject="Infagrab OTP",
        message=f"Your OTP is {otp}",
        from_email=None,
        recipient_list=[email],
    )
