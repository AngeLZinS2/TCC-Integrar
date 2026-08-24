from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification, NotificationPreference
from .serializers import NotificationPreferenceSerializer, NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    """
    Listagem e gerenciamento de notificações do usuário autenticado.
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        updated_count = self.get_queryset().filter(read=False).update(read=True)
        return Response({"status": "ok", "updated": updated_count})

    @action(detail=True, methods=["post", "patch"], url_path="read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.read = True
        notification.save()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)


class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/v1/notifications/preferences/

    Cria o registro na primeira visita, com todos os padrões — assim a tela
    não precisa lidar com "ainda não existe".
    """

    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        preferencia, _ = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preferencia
