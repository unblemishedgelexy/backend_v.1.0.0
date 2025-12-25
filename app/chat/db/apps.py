from django.apps import AppConfig

class ChatConfig(AppConfig):
    name = 'chat'

    def ready(self):
        from .db.mongo import get_db
        get_db()  # force connection
