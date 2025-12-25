import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db import transaction
from django.db.models import Q

import requests
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import E2EEIdentity, DMConversation, DMMessage


# -------------------------------------------------------------------
# Auth helper (same behaviour as tumhare chat_service wali)
# -------------------------------------------------------------------
def introspect_token(request):
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth:
        return None
    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1]

    try:
        resp = requests.post(
            settings.AUTH_SERVER_VERIFY,
            json={"token": token},
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data.get("success"):
            return None

        user_payload = data.get("user", {}) or {}
        user_id = user_payload.get("user_id") or user_payload.get("id")
        if not user_id:
            return None

        username = user_payload.get("username") or f"user_{user_id}"

        return {
            "id": user_id,
            "username": username,
            **{
                k: v
                for k, v in user_payload.items()
                if k not in ["user_id", "id", "username"]
            },
        }
    except Exception:
        return None


# -------------------------------------------------------------------
# E2EE Identity API
# -------------------------------------------------------------------

@csrf_exempt
@require_http_methods(["POST"])
def register_identity(request):
    """
    POST /e2ee/identity/
    Body: { "public_key": "<base64>" }
    Current user ki E2EE public key register / update karega.
    """
    user = introspect_token(request)
    if not user:
        return JsonResponse({"success": False, "error": "Authentication required"}, status=401)

    try:
        body = json.loads(request.body.decode() or "{}")
    except Exception:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    public_key = body.get("public_key")
    if not public_key:
        return JsonResponse({"success": False, "error": "public_key required"}, status=400)

    obj, _ = E2EEIdentity.objects.update_or_create(
        user_id=str(user["id"]),
        defaults={"public_key": public_key},
    )

    return JsonResponse(
        {"success": True, "user_id": obj.user_id, "public_key": obj.public_key}
    )


@csrf_exempt
@require_http_methods(["GET"])
def get_identity(request, user_id):
    """
    GET /e2ee/identity/<user_id>/
    Kisi user ki E2EE public key laane ke liye.
    """
    try:
        ident = E2EEIdentity.objects.get(user_id=str(user_id))
    except E2EEIdentity.DoesNotExist:
        # ✅ JSON 404 instead of Django HTML page
        return JsonResponse(
            {"success": False, "error": "identity_not_found"},
            status=404,
        )

    return JsonResponse(
        {
            "success": True,
            "user_id": ident.user_id,
            "public_key": ident.public_key,
        }
    )


# -------------------------------------------------------------------
# DM list + create
# -------------------------------------------------------------------

@csrf_exempt
@require_http_methods(["GET", "POST"])
def dm_list_create(request):
    """
    GET  /e2ee/dm/               -> current user ke saare DM list
    POST /e2ee/dm/ { user_id }   -> iss user ke sath DM create / fetch
    """
    user = introspect_token(request)
    if not user:
        return JsonResponse({"success": False, "error": "Authentication required"}, status=401)

    uid = str(user["id"])

    # ---------- LIST ----------
    if request.method == "GET":
        dms = DMConversation.objects.filter(
            Q(user1_id=uid) | Q(user2_id=uid)
        ).order_by("-created_at")

        conversations = []
        for dm in dms:
            other_id = dm.user2_id if dm.user1_id == uid else dm.user1_id
            conversations.append(
                {
                    "id": str(dm.id),
                    "user1_id": dm.user1_id,
                    "user2_id": dm.user2_id,
                    "other_user_id": other_id,
                    "created_at": dm.created_at.isoformat(),
                }
            )

        return JsonResponse({"success": True, "conversations": conversations})

    # ---------- CREATE ----------
    try:
        body = json.loads(request.body.decode() or "{}")
    except Exception:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    other_id = body.get("user_id")
    if not other_id:
        return JsonResponse({"success": False, "error": "user_id required"}, status=400)

    other_id = str(other_id)

    if other_id == uid:
        return JsonResponse({"success": False, "error": "Cannot create DM with yourself"}, status=400)

    # sorted store
    u1, u2 = sorted([uid, other_id])

    with transaction.atomic():
        dm, created = DMConversation.objects.get_or_create(
            user1_id=u1,
            user2_id=u2,
        )

    # dono users ki public keys bhej dete hai (agar registered)
    identities = E2EEIdentity.objects.filter(user_id__in=[uid, other_id])
    key_map = {i.user_id: i.public_key for i in identities}

    return JsonResponse(
        {
            "success": True,
            "conversation": {
                "id": str(dm.id),
                "user1_id": dm.user1_id,
                "user2_id": dm.user2_id,
            },
            "keys": key_map,  # { "<user_id>": "<public_key>" }
            "created": created,
        },
        status=201 if created else 200,
    )


# -------------------------------------------------------------------
# DM messages (ciphertext only)
# -------------------------------------------------------------------

def user_can_access_dm(uid: str, dm: DMConversation) -> bool:
    return uid in {dm.user1_id, dm.user2_id}


@csrf_exempt
@require_http_methods(["GET", "POST"])
def dm_messages(request, conv_id):
    """
    GET  /e2ee/dm/<conv_id>/messages/        -> ciphertext list
    POST /e2ee/dm/<conv_id>/messages/        -> ciphertext create + WS broadcast
    Body (POST): { "nonce": "...", "ciphertext": "...", "metadata": {...} }
    """
    user = introspect_token(request)
    if not user:
        return JsonResponse({"success": False, "error": "Authentication required"}, status=401)

    uid = str(user["id"])
    dm = get_object_or_404(DMConversation, id=conv_id)

    if not user_can_access_dm(uid, dm):
        return JsonResponse({"success": False, "error": "Not a participant"}, status=403)

    # ---------- LIST ----------
    if request.method == "GET":
        msgs = DMMessage.objects.filter(conversation=dm).order_by("timestamp")
        data = [
            {
                "id": str(m.id),
                "sender_id": m.sender_id,
                "nonce": m.nonce,
                "ciphertext": m.ciphertext,
                "metadata": m.metadata,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in msgs
        ]
        return JsonResponse({"success": True, "messages": data})

    # ---------- SEND ----------
    try:
        body = json.loads(request.body.decode() or "{}")
    except Exception:
        return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)

    nonce = body.get("nonce")
    ciphertext = body.get("ciphertext")
    metadata = body.get("metadata") or {}

    if not nonce or not ciphertext:
        return JsonResponse(
            {"success": False, "error": "nonce and ciphertext required"},
            status=400,
        )

    msg = DMMessage.objects.create(
        conversation=dm,
        sender_id=uid,
        nonce=nonce,
        ciphertext=ciphertext,
        metadata=metadata,
    )

    # WS broadcast to both DM participants
    channel_layer = get_channel_layer()

    payload = {
        "type": "e2ee_message",           # 👈 frontend data.type === "e2ee_message"
        "conversationId": str(dm.id),
        "id": str(msg.id),
        "sender_id": uid,
        "nonce": msg.nonce,
        "ciphertext": msg.ciphertext,
        "metadata": msg.metadata,
        "timestamp": msg.timestamp.isoformat(),
    }

    for target_id in [dm.user1_id, dm.user2_id]:
        async_to_sync(channel_layer.group_send)(
            f"user_{target_id}",          # same pattern: user_<auth_user_id>
            {
                "type": "chat.message",   # Channels consumer method
                "data": payload,
            },
        )

    return JsonResponse(
        {
            "success": True,
            "message_id": str(msg.id),
            "timestamp": msg.timestamp.isoformat(),
        },
        status=201,
    )
