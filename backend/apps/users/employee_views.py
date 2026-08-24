"""
Administração de colaboradores.

Separado de `views.py` (que cuida de autenticação e perfil) porque é outro
domínio: aqui o RH/admin administra as pessoas da empresa e o gestor
acompanha a própria equipe.

As estatísticas de progresso continuam em `apps/dashboard/` — este módulo
trata do cadastro em si.
"""

from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.common.query_params import parse_int_param

from . import rbac, scopes
from .models import User
from .permissions import HasPermission
from .serializers import EmployeeSerializer, RegisterSerializer

CanReadEmployees = HasPermission.require(
    rbac.EMPLOYEES_READ, message="Você não tem permissão para ver colaboradores."
)


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    CRUD de colaboradores da própria empresa.

    Escopo por papel (aplicado no queryset, nunca só na interface):
      - company_admin / rh_admin → todos os colaboradores da empresa;
      - gestor                   → apenas a própria equipe;
      - colaborador              → apenas o próprio registro;
      - owner                    → nada (administra tenants, não pessoas).
    """

    serializer_class = EmployeeSerializer
    permission_classes = [CanReadEmployees]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        base = User.objects.select_related("sector", "position", "manager").exclude(
            role=rbac.ROLE_OWNER
        )
        queryset = scopes.visible_colaboradores(self.request.user, base)

        params = self.request.query_params

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search)
                | Q(email__icontains=search)
                | Q(registration_number__icontains=search)
            )

        sector_id = parse_int_param(params.get("sector"), param_name="sector")
        if sector_id:
            queryset = queryset.filter(sector_id=sector_id)

        position_id = parse_int_param(params.get("position"), param_name="position")
        if position_id:
            queryset = queryset.filter(position_id=position_id)

        manager_id = parse_int_param(params.get("manager"), param_name="manager")
        if manager_id:
            queryset = queryset.filter(manager_id=manager_id)

        role = params.get("role")
        if role:
            queryset = queryset.filter(role=role)

        is_active = params.get("is_active")
        if is_active in ("true", "false"):
            queryset = queryset.filter(is_active=(is_active == "true"))

        return queryset.order_by("full_name")

    def get_serializer_class(self):
        if self.action == "create":
            return RegisterSerializer
        return EmployeeSerializer

    def _require(self, permission_code):
        if not self.request.user.has_perm_code(permission_code):
            raise PermissionDenied("Você não tem permissão para executar esta ação.")

    def create(self, request, *args, **kwargs):
        self._require(rbac.EMPLOYEES_CREATE)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        # Empresa vem sempre do usuário autenticado — nunca do corpo da
        # requisição, para impedir cadastro em outro tenant.
        user = serializer.save(company=self.request.user.company)
        password = serializer.validated_data.get("password")
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])

        audit.record(
            self.request.user,
            AuditLog.Action.CREATE,
            "employee",
            resource_id=user.pk,
            resource_label=user.full_name,
        )

    def update(self, request, *args, **kwargs):
        self._require(rbac.EMPLOYEES_UPDATE)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self._require(rbac.EMPLOYEES_UPDATE)
        return super().partial_update(request, *args, **kwargs)

    def perform_update(self, serializer):
        papel_antes = serializer.instance.role
        user = serializer.save()

        campos = audit.changed_field_names(serializer.validated_data)
        # Troca de papel muda o que a pessoa pode fazer no sistema — merece
        # uma ação própria no histórico, não some dentro de "alterou".
        mudou_papel = "role" in serializer.validated_data and user.role != papel_antes

        audit.record(
            self.request.user,
            AuditLog.Action.ROLE_CHANGE if mudou_papel else AuditLog.Action.UPDATE,
            "employee",
            resource_id=user.pk,
            resource_label=user.full_name,
            metadata=(
                {"from": papel_antes, "to": user.role}
                if mudou_papel
                else {"changed_fields": campos}
            ),
        )

    @action(detail=False, methods=["get"], url_path="manager-options")
    def manager_options(self, request):
        """Pessoas que podem ser escolhidas como gestor de um colaborador."""
        candidates = (
            User.objects.filter(
                company_id=request.user.company_id,
                is_active=True,
                role__in=[rbac.ROLE_GESTOR, rbac.ROLE_RH_ADMIN, rbac.ROLE_COMPANY_ADMIN],
            )
            .order_by("full_name")
            .values("id", "full_name", "role")
        )
        return Response(list(candidates))

    @action(detail=False, methods=["get"], url_path="roles")
    def roles(self, request):
        """Papéis atribuíveis dentro da empresa, para popular o seletor."""
        labels = dict(User.ROLE_CHOICES)
        return Response(
            [{"value": r, "label": labels[r]} for r in User.ASSIGNABLE_ROLES]
        )

    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        """
        Ativa/desativa preservando o histórico — nunca exclui.

        Mantém a proteção do último administrador: a empresa não pode ficar
        sem ninguém capaz de administrá-la.
        """
        self._require(rbac.EMPLOYEES_DEACTIVATE)
        target = self.get_object()

        if target.is_active and target.manages_company:
            others = (
                User.objects.filter(
                    company_id=target.company_id,
                    role__in=rbac.COMPANY_MANAGEMENT_ROLES,
                    is_active=True,
                )
                .exclude(pk=target.pk)
                .exists()
            )
            if not others:
                return Response(
                    {"detail": "Não é possível desativar o último administrador ativo da empresa."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])

        audit.record(
            request.user,
            AuditLog.Action.ACTIVATE if target.is_active else AuditLog.Action.DEACTIVATE,
            "employee",
            resource_id=target.pk,
            resource_label=target.full_name,
        )
        return Response(EmployeeSerializer(target).data)
