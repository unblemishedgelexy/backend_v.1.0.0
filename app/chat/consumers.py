# chat_app/consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from urllib.parse import parse_qs
from django.conf import settings
import jwt


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        # query params: ?token=...&userId=...
        query = parse_qs(self.scope["query_string"].decode())
        token = query.get("token", [None])[0]
        user_id = query.get("userId", [None])[0]

        # yaha tum simple JWT decode / verify kar sakte ho
        # ya auth server pe verify call karo (jitna tum already kar rahe ho)
        if not token or not user_id:
            await self.close()
            return

        self.user_id = str(user_id)
        self.group_name = f"user_{self.user_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Agar future me client se messages aayenge to handle karna
        # Abhi hum sirf server -> client push kar rahe hai.
        pass

    async def chat_message(self, event):
        """
        group_send me "type": "chat.message" aata hai,
        to ye method call hoga.
        event["data"] me humne payload dala hai (message / e2ee_message / conversation_created).
        """
        await self.send_json(event["data"])
