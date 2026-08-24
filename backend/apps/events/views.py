from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.common.segmentation import narrow_to_user
from apps.notifications.channels import Category, notify

from . import services
from .models import Event, EventAttendance
from .serializers import (
    BirthdaySerializer,
    EventAttendanceSerializer,
    EventSerializer,
    RSVPSerializer,
)

User = get_user_model()


def eventos_visiveis(user):
    """
    Eventos que `user` enxerga.

    Segmentação por setor e unidade com a mesma semântica dos comunicados:
    alvo vazio significa empresa inteira, e as dimensões afunilam entre si
    ("TI" + "Unidade Centro" = o TI da Centro). Quem administra vê tudo,
    inclusive o que é de outro setor, porque precisa gerenciar a agenda.
    """
    if not user.is_authenticated or not user.company_id:
        return Event.objects.none()

    queryset = Event.objects.filter(company_id=user.company_id)
    if user.manages_company:
        return queryset

    return narrow_to_user(
        queryset,
        user,
        [
            (Event.target_sectors, "sector_id", "event_id", user.sector_id, "setor"),
            (Event.target_units, "unit_id", "event_id", user.unit_id, "unidade"),
        ],
    )


class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # `confirmed_count` anotado: sem isto a listagem faria uma query de
        # contagem por evento.
        queryset = (
            eventos_visiveis(self.request.user)
            .select_related("organizer__sector", "organizer__position")
            # M2M serializados como lista de ids: sem prefetch o DRF
            # consulta a intermediaria uma vez por evento.
            .prefetch_related("target_sectors", "target_units")
            .annotate(
                _confirmed_count=Count(
                    "attendances",
                    filter=Q(attendances__status=EventAttendance.Status.GOING),
                    distinct=True,
                )
            )
        )

        params = self.request.query_params

        # O recorte por data vale só para a LISTAGEM. Aplicá-lo em todas as
        # rotas tornaria um evento passado inalcançável por id — nem o
        # detalhe abriria, e o RSVP responderia 404 em vez de explicar que
        # o evento já aconteceu.
        if self.action == "list":
            if params.get("past") == "true":
                queryset = queryset.filter(start_at__lt=timezone.now())
            elif params.get("all") != "true":
                queryset = queryset.filter(start_at__gte=timezone.now())

        if params.get("status"):
            queryset = queryset.filter(status=params["status"])

        ordem = "-start_at" if params.get("past") == "true" else "start_at"
        return queryset.order_by(ordem)

    def get_serializer_context(self):
        contexto = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated:
            # Uma query só para saber o que este usuário respondeu, em vez
            # de uma por evento na listagem.
            contexto["minhas_respostas"] = dict(
                EventAttendance.objects.filter(user=user).values_list(
                    "event_id", "status"
                )
            )
        return contexto

    def _exigir_gestao(self):
        if not self.request.user.manages_company:
            raise PermissionDenied("Apenas RH ou administrador podem gerenciar eventos.")

    # A permissao e conferida ANTES da validacao do corpo. Sem isto, quem
    # nao pode criar recebia 400 por um campo faltando em vez de 403 — a
    # mensagem errada, e que ainda revela o formato esperado.
    def create(self, request, *args, **kwargs):
        self._exigir_gestao()
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self._exigir_gestao()
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self._exigir_gestao()
        return super().partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        self._exigir_gestao()
        evento = serializer.save(
            company=self.request.user.company, organizer=self.request.user
        )
        audit.record(
            self.request.user, AuditLog.Action.CREATE, "event",
            resource_id=evento.pk, resource_label=evento.title,
        )

    def perform_update(self, serializer):
        self._exigir_gestao()
        evento = serializer.save()
        audit.record(
            self.request.user, AuditLog.Action.UPDATE, "event",
            resource_id=evento.pk, resource_label=evento.title,
            metadata={"changed_fields": audit.changed_field_names(serializer.validated_data)},
        )

    def perform_destroy(self, instance):
        self._exigir_gestao()
        audit.record(
            self.request.user, AuditLog.Action.DELETE, "event",
            resource_id=instance.pk, resource_label=instance.title,
        )
        instance.delete()

    @action(detail=True, methods=["post"], url_path="rsvp")
    def rsvp(self, request, pk=None):
        """
        Confirma ou recusa presença.

        A vaga é conferida dentro de uma transação com a linha do evento
        travada: sem isso, duas pessoas clicando ao mesmo tempo na última
        vaga entrariam as duas.
        """
        evento = self.get_object()

        if not evento.allows_rsvp:
            return Response(
                {"detail": "Este evento não pede confirmação de presença."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if evento.status == Event.Status.CANCELLED:
            return Response(
                {"detail": "Este evento foi cancelado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if evento.is_past:
            return Response(
                {"detail": "Este evento já aconteceu."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RSVPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        resposta = serializer.validated_data["status"]

        with transaction.atomic():
            travado = Event.objects.select_for_update().get(pk=evento.pk)
            atual = EventAttendance.objects.filter(
                event=travado, user=request.user
            ).first()
            ja_confirmado = atual and atual.status == EventAttendance.Status.GOING

            if resposta == EventAttendance.Status.GOING and not ja_confirmado:
                if travado.capacity:
                    confirmados = travado.attendances.filter(
                        status=EventAttendance.Status.GOING
                    ).count()
                    if confirmados >= travado.capacity:
                        return Response(
                            {"detail": "Este evento já atingiu a capacidade máxima."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

            EventAttendance.objects.update_or_create(
                event=travado, user=request.user, defaults={"status": resposta}
            )

        # Relê pelo queryset anotado: `refresh_from_db()` recarrega as
        # colunas, mas não recalcula `annotate` — o objeto continuaria com a
        # contagem anterior ao RSVP.
        atualizado = self.get_queryset().get(pk=evento.pk)
        return Response(
            EventSerializer(atualizado, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=["get"], url_path="attendees")
    def participantes(self, request, pk=None):
        """Lista de confirmados — só para quem organiza."""
        self._exigir_gestao()
        evento = self.get_object()
        registros = (
            evento.attendances.select_related("user", "user__sector")
            .filter(status=EventAttendance.Status.GOING)
            .order_by("user__full_name")
        )
        pagina = self.paginate_queryset(registros)
        serializer = EventAttendanceSerializer(
            pagina if pagina is not None else registros, many=True
        )
        if pagina is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancelar(self, request, pk=None):
        """
        Cancela o evento e avisa quem havia confirmado.

        Cancelar em vez de excluir: quem se programou precisa ser avisado, e
        excluir apagaria as confirmações sem deixar rastro.
        """
        self._exigir_gestao()
        evento = self.get_object()

        if evento.status == Event.Status.CANCELLED:
            return Response(
                {"detail": "Este evento já está cancelado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        evento.status = Event.Status.CANCELLED
        evento.save(update_fields=["status"])

        confirmados = [
            registro.user
            for registro in evento.attendances.filter(
                status=EventAttendance.Status.GOING
            ).select_related("user")
        ]
        if confirmados:
            notify(
                confirmados,
                f"Evento cancelado: {evento.title}",
                "O evento em que você confirmou presença foi cancelado.",
                category=Category.EVENT,
                email=True,
                link=f"/events/{evento.pk}",
            )

        audit.record(
            request.user, AuditLog.Action.UPDATE, "event",
            resource_id=evento.pk, resource_label=evento.title,
            metadata={"action": "cancelled", "notified": len(confirmados)},
        )
        atualizado = self.get_queryset().get(pk=evento.pk)
        return Response(
            EventSerializer(atualizado, context=self.get_serializer_context()).data
        )


class UpcomingBirthdaysView(APIView):
    """
    GET /api/v1/events/birthdays/

    Aniversariantes dos próximos 30 dias, da própria empresa.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        usuarios = User.objects.filter(
            company=request.user.company, is_active=True
        ).select_related("sector", "position").exclude(role="owner")

        proximos = services.proximos_aniversariantes(usuarios)
        return Response(
            {"results": [BirthdaySerializer(u).data for _, u in proximos]}
        )
