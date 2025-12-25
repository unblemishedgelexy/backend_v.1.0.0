from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('conversations/', views.conversation_list_create, name='conversations'),
    path('users/', views.user_list, name='user_list'),
    path('conversations/<uuid:conv_id>/messages/', views.messages_list_send, name='messages'),
    path('conversations/<uuid:conv_id>/add-member/', views.conversation_add_member, name='add_member'),
    path('conversations/<uuid:conv_id>/leave/', views.conversation_leave, name='leave_conversation'),
    path('conversations/<uuid:conv_id>/participants/', views.get_participants, name='participants'),
    path('groups/create/', views.create_group, name='create_group'),
    path('conversations/<uuid:conv_id>/add-bot/', views.add_bot_to_conversation, name='add_bot'),
]