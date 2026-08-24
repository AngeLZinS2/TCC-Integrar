"""
Configurações da própria empresa, para o admin do tenant.

Distinto de `CompanyViewSet`, que é do dono da plataforma e administra
TODAS as empresas. Aqui o escopo é sempre `request.user.company` — o id
nunca vem da URL nem do corpo, então não existe superfície para trocar de
tenant manipulando parâmetro.
"""

from django.db.models import Exists, OuterRef
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.courses.models import Course
from apps.sectors.models import Position, Sector
from apps.users import rbac
from apps.users.models import User

from .models import Company


class MyCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "legal_name",
            "cnpj",
            "description",
            "phone",
            "email",
            "address",
            "logo_url",
            "is_active",
            "created_at",
        ]
        # Ativar/suspender é decisão comercial da plataforma, não da empresa.
        read_only_fields = ["id", "is_active", "created_at"]


class MyCompanyView(APIView):
    """
    GET   /api/v1/companies/me/  → dados da própria empresa
    PATCH /api/v1/companies/me/  → atualiza (exige company.update)
    """

    permission_classes = [IsAuthenticated]

    def _company(self, request):
        return request.user.company

    def get(self, request):
        if not request.user.has_perm_code(rbac.COMPANY_READ) or not request.user.company_id:
            return Response(
                {"detail": "Você não tem uma empresa associada."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(MyCompanySerializer(self._company(request)).data)

    def patch(self, request):
        if not request.user.has_perm_code(rbac.COMPANY_UPDATE):
            return Response(
                {"detail": "Apenas o administrador da empresa pode alterar estes dados."},
                status=status.HTTP_403_FORBIDDEN,
            )
        company = self._company(request)
        serializer = MyCompanySerializer(company, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        audit.record(
            request.user,
            AuditLog.Action.UPDATE,
            "company",
            resource_id=company.pk,
            resource_label=company.name,
            metadata={"changed_fields": audit.changed_field_names(serializer.validated_data)},
        )
        return Response(serializer.data)


class CompanySetupChecklistView(APIView):
    """
    GET /api/v1/companies/me/setup/

    Checklist de primeira configuração. Cada passo é derivado do estado real
    do banco — não há flag "já configurei" para desincronizar da realidade.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.has_perm_code(rbac.COMPANY_READ) or not user.company_id:
            return Response(
                {"detail": "Você não tem uma empresa associada."},
                status=status.HTTP_403_FORBIDDEN,
            )

        company = user.company
        company_id = company.pk

        setores = Sector.objects.filter(company_id=company_id)
        tem_setor = setores.exists()
        tem_cargo = Position.objects.filter(sector__company_id=company_id).exists()
        tem_colaborador = User.objects.filter(
            company_id=company_id, role=rbac.ROLE_COLABORADOR
        ).exists()
        tem_gestor = (
            setores.annotate(
                com_gestor=Exists(
                    User.objects.filter(pk=OuterRef("manager_id"), is_active=True)
                )
            )
            .filter(com_gestor=True)
            .exists()
            or User.objects.filter(company_id=company_id, role=rbac.ROLE_GESTOR).exists()
        )
        tem_treinamento = Course.objects.filter(company_id=company_id).exists()
        dados_preenchidos = bool(company.cnpj or company.legal_name or company.address)

        passos = [
            {
                "key": "company_info",
                "title": "Informações da empresa",
                "description": "Preencha razão social, CNPJ e contato.",
                "done": dados_preenchidos,
                "route": "/company/settings",
            },
            {
                "key": "first_sector",
                "title": "Primeiro setor criado",
                "description": "Crie os setores da sua estrutura organizacional.",
                "done": tem_setor,
                "route": "/org/sectors",
            },
            {
                "key": "first_position",
                "title": "Primeiro cargo criado",
                "description": "Cadastre os cargos de cada setor.",
                "done": tem_cargo,
                "route": "/org/positions",
            },
            {
                "key": "first_employee",
                "title": "Primeiro colaborador cadastrado",
                "description": "Convide as pessoas da sua empresa.",
                "done": tem_colaborador,
                "route": "/rh/collaborators/new",
            },
            {
                "key": "first_manager",
                "title": "Primeiro gestor definido",
                "description": "Defina quem responde por cada setor.",
                "done": tem_gestor,
                "route": "/org/sectors",
            },
            {
                "key": "first_training",
                "title": "Primeiro treinamento criado",
                "description": "Monte a trilha de integração.",
                "done": tem_treinamento,
                "route": "/courses/new",
            },
        ]

        concluidos = sum(1 for p in passos if p["done"])
        return Response(
            {
                "steps": passos,
                "completed_steps": concluidos,
                "total_steps": len(passos),
                "percent": round(concluidos / len(passos) * 100),
                "is_complete": concluidos == len(passos),
            }
        )
