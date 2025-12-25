from celery import shared_task
from django.core.mail import send_mail

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=5, retry_kwargs={"max_retries": 3})
def send_otp_email(self, email, otp):
    send_mail(
        subject="Infagrab OTP Verification",
        message=f"Your OTP is {otp}",
        from_email=None,
        recipient_list=[email],
    )
