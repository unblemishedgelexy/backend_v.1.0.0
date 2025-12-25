from django.urls import path
from . import views

urlpatterns = [
    path("identity/", views.register_identity, name="register_identity"),
    path("identity/<str:user_id>/", views.get_identity, name="get_identity"),
    path("dm/", views.dm_list_create, name="dm_list_create"),
    path("dm/<uuid:conv_id>/messages/", views.dm_messages, name="dm_messages"),
]
