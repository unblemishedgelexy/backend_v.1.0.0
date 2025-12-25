import uuid
from .r2_client import s3_client
import os

def upload_video_to_r2(file_path: str):
    file_key = f"videos/{uuid.uuid4()}.mp4"

    s3_client.upload_file(
        Filename=file_path,
        Bucket=os.getenv("R2_BUCKET_NAME"),
        Key=file_key,
        ExtraArgs={
            "ContentType": "video/mp4",
            "ACL": "public-read"
        }
    )

    return f"https://{os.getenv('R2_BUCKET_NAME')}.{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com/{file_key}"
