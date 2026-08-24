from django.utils.dateparse import parse_date
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.query_params import parse_int_param
from apps.users import rbac
from apps.users.permissions import HasPermission

from .models import AuditLog
from .serializers import AuditLogSerializer

CanReadAudit = HasPermission.require(
    rbac.AUDIT_READ, message="Você não tem permissão para ver o histórico de atividades."
)


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Histórico de atividades da própria empresa.

    Somente leitura, por definição: um log que pode ser editado ou apagado
    pela interface não serve como auditoria.
    """

    serializer_class = AuditLogSerializer
    permission_classes = [CanReadAudit]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.company_id:
            return AuditLog.objects.none()

        queryset = AuditLog.objects.filter(company_id=user.company_id).select_related("actor")
        params = self.request.query_params

        actor_id = parse_int_param(params.get("actor"), param_name="actor")
        if actor_id:
            queryset = queryset.filter(actor_id=actor_id)

        action_filter = params.get("action")
        if action_filter:
            queryset = queryset.filter(action=action_filter)

        resource_type = params.get("resource_type")
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)

        date_from = parse_date(params.get("date_from") or "")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)

        date_to = parse_date(params.get("date_to") or "")
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.order_by("-created_at")

    @action(detail=False, methods=["get"], url_path="filters")
    def filters(self, request):
        """Opções para montar os filtros da tela, sem o app adivinhar valores."""
        return Response(
            {
                "actions": [
                    {"value": value, "label": label}
                    for value, label in AuditLog.Action.choices
                ],
                "resource_types": sorted(
                    self.get_queryset()
                    .values_list("resource_type", flat=True)
                    .distinct()
                ),
            }
        )
