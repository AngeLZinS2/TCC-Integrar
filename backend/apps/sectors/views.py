from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.common.query_params import parse_int_param
from apps.users import rbac
from apps.users.models import User
from apps.users.permissions import ReadWritePermission

from .models import Position, Sector
from .serializers import PositionSerializer, SectorManagerOptionSerializer, SectorSerializer

CanManageSectors = ReadWritePermission.require(
    rbac.DEPARTMENTS_READ,
    rbac.DEPARTMENTS_CREATE,
    message="Você não tem permissão para gerenciar setores.",
)
CanManagePositions = ReadWritePermission.require(
    rbac.POSITIONS_READ,
    rbac.POSITIONS_CREATE,
    message="Você não tem permissão para gerenciar cargos.",
)


class SectorViewSet(viewsets.ModelViewSet):
    """
    CRUD de setores da própria empresa.

    As contagens de cargos e colaboradores vêm anotadas na mesma query da
    listagem — sem isso, a tela de Setores faria duas queries por linha.
    """

    serializer_class = SectorSerializer
    permission_classes = [CanManageSectors]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.company_id:
            return Sector.objects.none()

        queryset = (
            Sector.objects.filter(company_id=user.company_id)
            .select_related("manager")
            .prefetch_related("positions")
            .annotate(
                positions_count=Count("positions", distinct=True),
                collaborators_count=Count(
                    "users", filter=Q(users__is_active=True), distinct=True
                ),
            )
            .order_by("name")
        )

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        is_active = self.request.query_params.get("is_active")
        if is_active in ("true", "false"):
            queryset = queryset.filter(is_active=(is_active == "true"))

        return queryset

    def perform_create(self, serializer):
        # Empresa vem sempre do usuário autenticado — nunca do corpo da
        # requisição, para não permitir criar setor em outro tenant.
        sector = serializer.save(company=self.request.user.company)
        audit.record(
            self.request.user, AuditLog.Action.CREATE, "sector",
            resource_id=sector.pk, resource_label=sector.name,
        )

    def perform_update(self, serializer):
        sector = serializer.save()
        audit.record(
            self.request.user, AuditLog.Action.UPDATE, "sector",
            resource_id=sector.pk, resource_label=sector.name,
            metadata={"changed_fields": audit.changed_field_names(serializer.validated_data)},
        )

    def perform_destroy(self, instance):
        if instance.users.exists():
            raise ValidationError(
                {"detail": "Não é possível excluir um setor com colaboradores vinculados. "
                           "Desative-o ou mova os colaboradores antes."}
            )
        audit.record(
            self.request.user, AuditLog.Action.DELETE, "sector",
            resource_id=instance.pk, resource_label=instance.name,
        )
        instance.delete()

    @action(detail=True, methods=["get"], url_path="positions")
    def positions(self, request, pk=None):
        sector = self.get_object()
        positions = sector.positions.annotate(
            collaborators_count=Count("users", filter=Q(users__is_active=True), distinct=True)
        )
        return Response(PositionSerializer(positions, many=True).data)

    @action(detail=False, methods=["get"], url_path="manager-options")
    def manager_options(self, request):
        """
        Candidatos a gestor de setor: pessoas da empresa que podem assumir
        responsabilidade sobre uma equipe. Colaboradores comuns ficam fora
        da lista para não sugerir uma escolha que não faz sentido.
        """
        candidates = User.objects.filter(
            company_id=request.user.company_id,
            is_active=True,
            role__in=[rbac.ROLE_GESTOR, rbac.ROLE_RH_ADMIN, rbac.ROLE_COMPANY_ADMIN],
        ).order_by("full_name")
        return Response(SectorManagerOptionSerializer(candidates, many=True).data)


class PositionViewSet(viewsets.ModelViewSet):
    """
    CRUD de cargos. O tenant é garantido pelo setor: um cargo só existe
    dentro de um setor, e o setor pertence a uma empresa.
    """

    serializer_class = PositionSerializer
    permission_classes = [CanManagePositions]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.company_id:
            return Position.objects.none()

        queryset = (
            Position.objects.filter(sector__company_id=user.company_id)
            .select_related("sector")
            .annotate(
                collaborators_count=Count("users", filter=Q(users__is_active=True), distinct=True)
            )
            .order_by("sector__name", "name")
        )

        sector_id = parse_int_param(
            self.request.query_params.get("sector"), param_name="sector"
        )
        if sector_id:
            queryset = queryset.filter(sector_id=sector_id)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        is_active = self.request.query_params.get("is_active")
        if is_active in ("true", "false"):
            queryset = queryset.filter(is_active=(is_active == "true"))

        return queryset

    def perform_create(self, serializer):
        position = serializer.save()
        audit.record(
            self.request.user, AuditLog.Action.CREATE, "position",
            resource_id=position.pk, resource_label=position.name,
        )

    def perform_update(self, serializer):
        position = serializer.save()
        audit.record(
            self.request.user, AuditLog.Action.UPDATE, "position",
            resource_id=position.pk, resource_label=position.name,
            metadata={"changed_fields": audit.changed_field_names(serializer.validated_data)},
        )

    def perform_destroy(self, instance):
        if instance.users.exists():
            raise ValidationError(
                {"detail": "Não é possível excluir um cargo com colaboradores vinculados. "
                           "Desative-o ou mova os colaboradores antes."}
            )
        audit.record(
            self.request.user, AuditLog.Action.DELETE, "position",
            resource_id=instance.pk, resource_label=instance.name,
        )
        instance.delete()
