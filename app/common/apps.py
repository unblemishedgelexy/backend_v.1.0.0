from django.apps import AppConfig

class CommonConfig(AppConfig):
    name = "common"

    def ready(self):
        try:
            from .redis_client import redis_client
            redis_client.ping()
            print("✅ Redis connected")
        except Exception as e:
            print("⚠️ Redis not ready:", e)
