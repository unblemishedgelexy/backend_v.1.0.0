import json
import requests

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db import transaction
from django.db.models import Q

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Conversation, ConversationMember, Message


AUTH_USERS_URL = settings.AUTH_USERS_URL + '/users/'


# --------------------------------------------------------------------
# Auth helper – introspect Bearer token with auth server
# --------------------------------------------------------------------
def introspect_token(request):
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth:
        return None
    parts = auth.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    token = parts[1]
    try:
        resp = requests.post(settings.AUTH_SERVER_VERIFY, json={'token': token}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success'):
                user_payload = data.get('user', {})
                user_id = user_payload.get('user_id') or user_payload.get('id')

                username = user_payload.get('username')
                if not username:
                    username = f"user_{user_id}"

                return {
                    'id': user_id,
                    'username': username,
                    **{k: v for k, v in user_payload.items()
                       if k not in ['user_id', 'id', 'username']}
                }
    except Exception:
        return None
    return None


# --------------------------------------------------------------------
# Membership helper – robust + self-healing
# --------------------------------------------------------------------
def ensure_member(user, conversation):
    """
    Robust membership check.

    1. Try to find a ConversationMember row for this user
       (matches by id OR username OR legacy user_id=username).
    2. If not found but user is the creator, auto-add them as admin.
    3. Returns True if user is (or becomes) a member, else False.
    """
    uid = str(user['id'])
    uname = user.get('username') or ''

    member_qs = ConversationMember.objects.filter(
        conversation=conversation
    ).filter(
        Q(user_id=uid) | Q(username=uname) | Q(user_id=uname)
    )

    if member_qs.exists():
        return True

    # Self-heal: creator must always be a member
    if str(conversation.created_by_id) in {uid, uname} or conversation.created_by_username == uname:
        ConversationMember.objects.get_or_create(
            conversation=conversation,
            user_id=uid,
            defaults={
                'username': uname,
                'is_admin': True,
            },
        )
        return True

    return False


# --------------------------------------------------------------------
# Conversation list & create (DM / 1-1, but supports is_group flag)
# --------------------------------------------------------------------
@csrf_exempt
@require_http_methods(['GET', 'POST'])
def conversation_list_create(request):
    user = introspect_token(request)
    if not user:
        return JsonResponse(
            {'success': False, 'error': 'Authentication required'},
            status=401
        )

    uid = str(user['id'])
    uname = user['username']

    # ---------- LIST CONVERSATIONS ----------
    if request.method == 'GET':
        convs = Conversation.objects.filter(
            Q(members__user_id=uid) |
            Q(members__user_id=uname) |
            Q(members__username=uname) |
            Q(created_by_id=uid) |
            Q(created_by_username=uname)
        ).distinct()

        data = [
            {
                'id': str(c.id),
                'is_group': c.is_group,
                'name': c.name,
                'created_at': c.created_at.isoformat(),
            }
            for c in convs
        ]
        return JsonResponse({'success': True, 'conversations': data})

    # ---------- CREATE CONVERSATION ----------
    try:
        body = json.loads(request.body.decode() or "{}")
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    raw_participants = body.get('participants') or []
    is_group = bool(body.get('is_group', False))
    name = body.get('name') if is_group else None

    # Map of user_id -> username
    members_map = {uid: uname}  # current user always included

    for p in raw_participants:
        if isinstance(p, dict):
            pid = p.get('id') or p.get('user_id')
            puname = p.get('username')
        else:
            # fallback – treat value as username and id same as username
            pid = str(p)
            puname = str(p)

        if not pid:
            continue

        pid = str(pid)

        # don't re-add self
        if pid == uid:
            continue

        if not puname:
            puname = f"user_{pid}"

        members_map[pid] = puname

    if len(members_map) < 2:
        return JsonResponse(
            {'success': False, 'error': 'At least one other participant required'},
            status=400
        )

    with transaction.atomic():
        conv = Conversation.objects.create(
            is_group=is_group,
            name=name or '',
            created_by_id=uid,
            created_by_username=uname,
        )

        for member_id, member_username in members_map.items():
            ConversationMember.objects.create(
                conversation=conv,
                user_id=str(member_id),      # ALWAYS auth id / stable id
                username=member_username,
                is_admin=(member_id == uid),
            )

    # 🔔 broadcast "conversation_created" to all members
    channel_layer = get_channel_layer()
    members = ConversationMember.objects.filter(conversation=conv)

    payload = {
        "type": "conversation_created",
        "conversation": {
            "id": str(conv.id),
            "is_group": conv.is_group,
            "name": conv.name,
            "created_at": conv.created_at.isoformat(),
        },
    }

    for m in members:
        async_to_sync(channel_layer.group_send)(
            f"user_{m.user_id}",
            {
                "type": "chat.message",
                "data": payload,
            },
        )

    return JsonResponse({'success': True, 'conversation_id': str(conv.id)}, status=201)


# --------------------------------------------------------------------
# Messages list / send
# --------------------------------------------------------------------
@csrf_exempt
@require_http_methods(['GET', 'POST'])
def messages_list_send(request, conv_id):
    user = introspect_token(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)

    conv = get_object_or_404(Conversation, id=conv_id)

    if not ensure_member(user, conv):
        return JsonResponse({'success': False, 'error': 'Not a participant'}, status=403)

    # ---------- LIST MESSAGES ----------
    if request.method == 'GET':
        limit = int(request.GET.get('limit', 50))
        messages = Message.objects.filter(conversation=conv).order_by('-timestamp')[:limit]
        msgs = []
        for m in reversed(messages):
            msgs.append({
                'id': str(m.id),
                'sender_id': m.sender_id,
                'sender_username': m.sender_username,
                'ciphertext': m.ciphertext,
                'metadata': m.metadata,
                'timestamp': m.timestamp.isoformat(),
            })
        return JsonResponse({'success': True, 'messages': msgs})

    # ---------- SEND MESSAGE ----------
    try:
        body = json.loads(request.body.decode() or "{}")
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    ciphertext = body.get('ciphertext')
    metadata = body.get('metadata')
    if not ciphertext:
        return JsonResponse({'success': False, 'error': 'ciphertext required'}, status=400)

    msg = Message.objects.create(
        conversation=conv,
        sender_id=str(user['id']),
        sender_username=user['username'],
        ciphertext=ciphertext,
        metadata=metadata or {}
    )

    # 🔔 REALTIME BROADCAST via Channels
    channel_layer = get_channel_layer()

    payload = {
        "type": "message",  # frontend data.type === "message"
        "conversationId": str(conv.id),
        "id": str(msg.id),
        "sender_id": str(user['id']),
        "sender_username": user['username'],
        "ciphertext": msg.ciphertext,
        "metadata": msg.metadata or {},
        "timestamp": msg.timestamp.isoformat(),
        "status": "sent",
    }

    members = ConversationMember.objects.filter(conversation=conv)
    for m in members:
        async_to_sync(channel_layer.group_send)(
            f"user_{m.user_id}",
            {
                "type": "chat.message",
                "data": payload,
            },
        )

    return JsonResponse(
        {
            'success': True,
            'message_id': str(msg.id),
            'timestamp': msg.timestamp.isoformat(),
        },
        status=201
    )


# --------------------------------------------------------------------
# Users list (proxy to auth server) + bot
# --------------------------------------------------------------------
@csrf_exempt
@require_http_methods(['GET'])
def user_list(request):
    user = introspect_token(request)
    if not user:
        return JsonResponse(
            {'success': False, 'error': 'Authentication required'},
            status=401
        )

    search = request.GET.get('search', '')
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 20)

    try:
        resp = requests.get(
            AUTH_USERS_URL,
            params={
                'search': search,
                'page': page,
                'page_size': page_size,
            },
            headers={
                'Authorization': request.META.get('HTTP_AUTHORIZATION', ''),
            },
            timeout=5,
        )
        if resp.status_code != 200:
            return JsonResponse(
                {'success': False, 'error': 'Auth server error'},
                status=502
            )
        data = resp.json()
    except Exception:
        return JsonResponse(
            {'success': False, 'error': 'Auth server unreachable'},
            status=502
        )

    results = []
    for u in data.get('results', []):
        results.append({
            "id": str(u.get('id') or u.get('user_id')),
            "username": u.get('username'),
            "is_bot": False,
        })

    # add chatbot entry only on first page & no search
    if str(page) == '1' and not search:
        results.append({
            "id": "aibot",
            "username": "aibot",
            "is_bot": True,
        })

    return JsonResponse({
        "success": True,
        "results": results,
        "page": data.get('page', int(page)),
        "page_size": data.get('page_size', int(page_size)),
        "has_next": data.get('has_next', False),
    })


# --------------------------------------------------------------------
# Add member to conversation
# --------------------------------------------------------------------
@csrf_exempt
@require_http_methods(['POST'])
def conversation_add_member(request, conv_id):
    user = introspect_token(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)

    conv = get_object_or_404(Conversation, id=conv_id)

    uid = str(user['id'])
    uname = user['username']

    # must be admin to add members
    if not ConversationMember.objects.filter(
        conversation=conv
    ).filter(
        Q(user_id=uid) | Q(username=uname) | Q(user_id=uname),
        is_admin=True
    ).exists():
        return JsonResponse({'success': False, 'error': 'Admin required to add members'}, status=403)

    try:
        body = json.loads(request.body.decode() or "{}")
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    new_members = body.get('members', [])
    if not new_members:
        return JsonResponse({'success': False, 'error': 'members list required'}, status=400)

    added = []

    for m in new_members:
        if isinstance(m, dict):
            mid = m.get('id') or m.get('user_id')
            musername = m.get('username')
        else:
            mid = str(m)
            musername = str(m)

        if not mid:
            continue

        mid = str(mid)
        if not musername:
            musername = f"user_{mid}"

        obj, created = ConversationMember.objects.get_or_create(
            conversation=conv,
            user_id=mid,
            defaults={'username': musername}
        )
        if created:
            added.append(musername)

    return JsonResponse({'success': True, 'added': added})


# --------------------------------------------------------------------
# Leave conversation
# --------------------------------------------------------------------
@csrf_exempt
@require_http_methods(['POST'])
def conversation_leave(request, conv_id):
    user = introspect_token(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)

    conv = get_object_or_404(Conversation, id=conv_id)

    uid = str(user['id'])
    uname = user['username']

    ConversationMember.objects.filter(
        conversation=conv
    ).filter(
        Q(user_id=uid) | Q(username=uname) | Q(user_id=uname)
    ).delete()

    return JsonResponse({'success': True, 'message': 'left'})


# --------------------------------------------------------------------
# Get participants (this endpoint was giving 403)
# --------------------------------------------------------------------
@csrf_exempt
@require_http_methods(['GET'])
def get_participants(request, conv_id):
    user = introspect_token(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)

    conv = get_object_or_404(Conversation, id=conv_id)

    if not ensure_member(user, conv):
        return JsonResponse({'success': False, 'error': 'Not a participant'}, status=403)

    members = ConversationMember.objects.filter(conversation=conv)
    data = [
        {
            'username': m.username,
            'user_id': m.user_id,
            'is_admin': m.is_admin
        }
        for m in members
    ]
    return JsonResponse({'success': True, 'members': data})


# --------------------------------------------------------------------
# Create group conversation
# --------------------------------------------------------------------
@csrf_exempt
@require_http_methods(['POST'])
def create_group(request):
    user = introspect_token(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)

    try:
        body = json.loads(request.body.decode() or "{}")
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    name = body.get('name')
    members_payload = body.get('members', [])

    if not name or not members_payload:
        return JsonResponse(
            {'success': False, 'error': 'name and members are required'},
            status=400
        )

    uid = str(user['id'])
    uname = user['username']

    members_map = {uid: uname}  # current user always included

    for m in members_payload:
        if isinstance(m, dict):
            mid = m.get('id') or m.get('user_id')
            musername = m.get('username')
        else:
            mid = None
            musername = str(m)

        if not musername and not mid:
            continue

        if not mid:
            mid = musername

        mid = str(mid)
        if mid == uid:
            continue

        if not musername:
            musername = f"user_{mid}"

        members_map[mid] = musername

    if len(members_map) < 2:
        return JsonResponse(
            {'success': False, 'error': 'Need at least 2 members for group'},
            status=400
        )

    channel_layer = get_channel_layer()

    with transaction.atomic():
        conv = Conversation.objects.create(
            is_group=True,
            name=name,
            created_by_id=uid,
            created_by_username=uname,
        )

        for member_id, member_username in members_map.items():
            ConversationMember.objects.create(
                conversation=conv,
                user_id=member_id,
                username=member_username,
                is_admin=(member_id == uid),
            )

    payload = {
        "type": "conversation_created",
        "conversation": {
            "id": str(conv.id),
            "is_group": conv.is_group,
            "name": conv.name,
            "created_at": conv.created_at.isoformat(),
        },
    }

    for member_id in members_map.keys():
        async_to_sync(channel_layer.group_send)(
            f"user_{member_id}",
            {
                "type": "chat.message",
                "data": payload,
            },
        )

    return JsonResponse({'success': True, 'conversation_id': str(conv.id)}, status=201)


# --------------------------------------------------------------------
# Add bot to conversation
# --------------------------------------------------------------------
@csrf_exempt
@require_http_methods(['POST'])
def add_bot_to_conversation(request, conv_id):
    user = introspect_token(request)
    if not user:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)

    conv = get_object_or_404(Conversation, id=conv_id)

    uid = str(user['id'])
    uname = user['username']

    if not ConversationMember.objects.filter(
        conversation=conv
    ).filter(
        Q(user_id=uid) | Q(username=uname) | Q(user_id=uname),
        is_admin=True
    ).exists():
        return JsonResponse({'success': False, 'error': 'Admin required to add bot'}, status=403)

    bot_username = 'aibot'
    ConversationMember.objects.get_or_create(
        conversation=conv,
        user_id=bot_username,
        defaults={'username': bot_username}
    )

    return JsonResponse({'success': True, 'bot_added': bot_username})
