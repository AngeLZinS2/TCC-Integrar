import csv

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.dashboard import services as dashboard_services
from apps.users.permissions import IsOwner

from .models import Company
from .serializers import CompanyBootstrapSerializer, CompanySerializer


def _company_summary(company):
    """Empresa + estatísticas agregadas resumidas, para list/detail/ações."""
    overview = dashboard_services.get_dashboard_overview(company=company)
    return {
        "id": company.id,
        "name": company.name,
        "is_active": company.is_active,
        "created_at": company.created_at,
        "total_collaborators": overview["total_collaborators"],
        "avg_course_completion_percent": overview["avg_course_completion_percent"],
        "avg_checklist_completion_percent": overview["avg_checklist_completion_percent"],
    }


class CompanyViewSet(viewsets.ViewSet):
    """
    Cadastro e acompanhamento de empresas clientes (tenants).
    Acesso restrito ao dono do sistema (IsOwner). Sem exclusão — apenas
    ativar/desativar via /toggle-active/.
    """

    permission_classes = [IsOwner]

    def list(self, request):
        companies = Company.objects.all().order_by("name")
        return Response([_company_summary(c) for c in companies])

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        companies = Company.objects.all().order_by("name")

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="empresas.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Nome", "Ativa", "Criada em", "Total de colaboradores", "% Cursos (média)", "% Checklist (média)",
        ])
        for company in companies:
            summary = _company_summary(company)
            writer.writerow([
                summary["name"],
                "Sim" if summary["is_active"] else "Não",
                summary["created_at"],
                summary["total_collaborators"],
                summary["avg_course_completion_percent"],
                summary["avg_checklist_completion_percent"],
            ])
        return response

    def create(self, request):
        serializer = CompanyBootstrapSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = serializer.save()
        return Response(_company_summary(company), status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        company = get_object_or_404(Company, pk=pk)
        return Response(_company_summary(company))

    def partial_update(self, request, pk=None):
        company = get_object_or_404(Company, pk=pk)
        serializer = CompanySerializer(company, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(_company_summary(company))

    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        company = get_object_or_404(Company, pk=pk)
        company.is_active = not company.is_active
        company.save(update_fields=["is_active"])
        return Response(_company_summary(company))

    @action(detail=True, methods=["get"], url_path="dashboard")
    def dashboard(self, request, pk=None):
        """
        Indicadores agregados da empresa — contagens, médias e distribuição.

        Nenhum campo aqui identifica um colaborador: o dono da plataforma
        administra o tenant, não as pessoas dentro dele. A listagem nominal
        de colaboradores existe apenas em /api/v1/dashboard/collaborators/,
        restrita ao RH da própria empresa.
        """
        company = get_object_or_404(Company, pk=pk)
        return Response(dashboard_services.get_dashboard_overview(company=company))
