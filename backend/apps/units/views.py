"""
CRUD de unidades.

Ler é baseline para qualquer colaborador — o app precisa mostrar de que
filial alguém é, e os formulários precisam da lista. Alterar exige
`company.update`: uma unidade errada reetiqueta todo mundo lotado nela.
"""

from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.users import rbac

from .models import Unit
from .serializers import UnitSerializer


class UnitViewSet(viewsets.ModelViewSet):
    serializer_class = UnitSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.company_id:
            return Unit.objects.none()

        queryset = (
            Unit.objects.filter(company_id=user.company_id)
            .select_related("manager")
            # Só os ativos entram na conta: um desligado ainda aponta para a
            # unidade, e contá-lo faria o painel do RH mostrar um quadro
            # maior do que o real.
            .annotate(
                employee_count=Count(
                    "employees", filter=Q(employees__is_active=True), distinct=True
                )
            )
            .order_by("name")
        )

        if valor := self.request.query_params.get("status"):
            queryset = queryset.filter(status=valor)
        return queryset

    def _exigir_gestao(self):
        if not self.request.user.has_perm_code(rbac.COMPANY_UPDATE):
            raise PermissionDenied("Você não pode gerenciar unidades.")

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
        unidade = serializer.save(company_id=self.request.user.company_id)
        audit.record(
            self.request.user, AuditLog.Action.CREATE, "unit",
            resource_id=unidade.pk, resource_label=unidade.name,
        )

    def perform_update(self, serializer):
        unidade = serializer.save()
        audit.record(
            self.request.user, AuditLog.Action.UPDATE, "unit",
            resource_id=unidade.pk, resource_label=unidade.name,
        )

    def perform_destroy(self, instance):
        audit.record(
            self.request.user, AuditLog.Action.DELETE, "unit",
            resource_id=instance.pk, resource_label=instance.name,
        )
        instance.delete()
