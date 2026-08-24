"""
Endpoints das automações.

Gerenciar automação exige `company.update` — e não uma permissão de RH.
Uma regra mal configurada dispara e-mails para a empresa inteira e atribui
treinamentos em massa; é decisão de administração, não rotina.
"""

from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.users import rbac

from . import catalog
from .models import AutomationRule, AutomationRun
from .serializers import AutomationRuleSerializer, AutomationRunSerializer


class AutomationCatalogView(APIView):
    """
    Eventos, ações e condições que o formulário pode oferecer.

    Servido pela API para o app não manter uma cópia da lista: uma cópia
    desatualizada ofereceria um gatilho que o backend recusa.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        def opcoes(pares):
            return [{"value": v, "label": r} for v, r in pares]

        return Response(
            {
                "events": opcoes(catalog.EVENT_CHOICES),
                "actions": opcoes(catalog.ACTION_CHOICES),
                "targets": opcoes(catalog.TARGET_CHOICES),
                "condition_fields": opcoes(catalog.CONDITION_FIELD_CHOICES),
                "operators": opcoes(catalog.OPERATOR_CHOICES),
            }
        )


class AutomationRuleViewSet(viewsets.ModelViewSet):
    serializer_class = AutomationRuleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.company_id:
            return AutomationRule.objects.none()

        queryset = (
            AutomationRule.objects.filter(company_id=user.company_id)
            .prefetch_related("conditions", "actions")
            .annotate(run_count=Count("runs", distinct=True))
            .order_by("name")
        )
        if valor := self.request.query_params.get("event"):
            queryset = queryset.filter(trigger_event=valor)
        return queryset

    def _exigir_gestao(self):
        if not self.request.user.has_perm_code(rbac.COMPANY_UPDATE):
            raise PermissionDenied("Você não pode gerenciar automações.")

    def list(self, request, *args, **kwargs):
        self._exigir_gestao()
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        self._exigir_gestao()
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        self._exigir_gestao()
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self._exigir_gestao()
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self._exigir_gestao()
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._exigir_gestao()
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        regra = serializer.save(
            company_id=self.request.user.company_id, created_by=self.request.user
        )
        audit.record(
            self.request.user, AuditLog.Action.CREATE, "automation",
            resource_id=regra.pk, resource_label=regra.name,
        )

    def perform_update(self, serializer):
        regra = serializer.save()
        audit.record(
            self.request.user, AuditLog.Action.UPDATE, "automation",
            resource_id=regra.pk, resource_label=regra.name,
        )

    def perform_destroy(self, instance):
        audit.record(
            self.request.user, AuditLog.Action.DELETE, "automation",
            resource_id=instance.pk, resource_label=instance.name,
        )
        instance.delete()

    @action(detail=True, methods=["get"], url_path="runs")
    def execucoes(self, request, pk=None):
        """
        Histórico de disparos.

        Sem isto, uma automação que falha em silêncio é indistinguível de
        uma que nunca foi acionada.
        """
        self._exigir_gestao()
        regra = self.get_object()
        execucoes = regra.runs.all()[:50]
        return Response(AutomationRunSerializer(execucoes, many=True).data)
