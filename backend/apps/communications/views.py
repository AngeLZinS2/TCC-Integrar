from django.db.models import Count, Exists, OuterRef
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.audit.models import AuditLog

from . import services
from .tasks import notificar_publico_alvo
from .models import Announcement, AnnouncementRead
from .serializers import AnnouncementCreateSerializer, AnnouncementSerializer

class AnnouncementListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AnnouncementCreateSerializer
        return AnnouncementSerializer

    def get_queryset(self):
        user = self.request.user
        # `is_read` e `read_count` faziam uma query por linha da lista.
        # Anotados aqui, a listagem inteira custa uma query só.
        return (
            services.visible_to(user)
            .annotate(
                _read_count=Count("reads", distinct=True),
                _is_read=Exists(
                    AnnouncementRead.objects.filter(
                        announcement_id=OuterRef("pk"), user_id=user.id
                    )
                ),
            )
            .prefetch_related("target_sectors", "target_positions", "target_units")
            .select_related("author")
        )

    def perform_create(self, serializer):
        if not self.request.user.manages_company:
            raise PermissionDenied("Apenas RH ou Admin podem criar comunicados.")

        comunicado = serializer.save(
            company=self.request.user.company,
            author=self.request.user,
        )

        # Com data futura, entra na fila do Beat; sem data, nasce rascunho e
        # o RH publica quando quiser. Publicar nunca e implicito.
        if comunicado.publish_at and comunicado.publish_at > timezone.now():
            comunicado.status = Announcement.Status.SCHEDULED
            comunicado.save(update_fields=["status"])

        audit.record(
            self.request.user, AuditLog.Action.CREATE, "announcement",
            resource_id=comunicado.pk, resource_label=comunicado.title,
            metadata={"status": comunicado.status},
        )


class AnnouncementDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AnnouncementSerializer

    def get_queryset(self):
        # Mesma regra da listagem: saber o id de um comunicado de outro
        # setor não pode ser suficiente para abri-lo.
        return services.visible_to(self.request.user)

    def perform_update(self, serializer):
        if not self.request.user.manages_company:
            raise PermissionDenied("Apenas RH ou Admin podem editar comunicados.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.manages_company:
            raise PermissionDenied("Apenas RH ou Admin podem excluir comunicados.")
        instance.delete()


class MarkAsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        announcement = get_object_or_404(services.visible_to(request.user), pk=pk)
        AnnouncementRead.objects.get_or_create(
            announcement=announcement,
            user=request.user
        )
        return Response({"status": "marked as read"}, status=status.HTTP_200_OK)


class AnnouncementPublishView(APIView):
    """
    POST /api/v1/communications/<pk>/publish/

    Publica agora e dispara a notificacao do publico-alvo pela fila. A
    notificacao nao acontece dentro deste request: numa empresa grande sao
    milhares de linhas, e o RH nao pode ficar esperando.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not request.user.manages_company:
            raise PermissionDenied("Apenas RH ou Admin podem publicar comunicados.")

        comunicado = get_object_or_404(
            Announcement.objects.filter(company_id=request.user.company_id), pk=pk
        )
        if comunicado.status == Announcement.Status.PUBLISHED:
            return Response(
                {"detail": "Este comunicado já está publicado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comunicado.status = Announcement.Status.PUBLISHED
        comunicado.published_at = timezone.now()
        comunicado.save(update_fields=["status", "published_at"])

        audit.record(
            request.user, AuditLog.Action.UPDATE, "announcement",
            resource_id=comunicado.pk, resource_label=comunicado.title,
            metadata={"action": "published"},
        )

        notificar_publico_alvo.delay(comunicado.pk)
        return Response(AnnouncementSerializer(comunicado, context={"request": request}).data)
