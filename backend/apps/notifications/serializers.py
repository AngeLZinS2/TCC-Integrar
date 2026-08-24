from rest_framework import serializers

from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "message", "read", "link", "created_at"]
        read_only_fields = ["id", "created_at", "link"]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Preferências do próprio usuário.

    `user` nunca entra: o dono do registro vem sempre do token, para
    ninguém alterar a preferência de outra pessoa.
    """

    class Meta:
        model = NotificationPreference
        exclude = ["id", "user"]
