import csv

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.query_params import parse_int_param
from apps.users.models import User
from apps.users.permissions import IsRHAdmin

from . import services
from .serializers import (
    CollaboratorDetailSerializer,
    CollaboratorStatsSerializer,
    DashboardOverviewSerializer,
)


def _collaborator_filters(request) -> dict:
    """
    Filtros aceitos na listagem e na exportação.

    Compartilhado de propósito: se a exportação aceitasse um filtro que a
    listagem não aceita (ou vice-versa), o CSV poderia devolver mais do que
    a tela mostra. Aqui os dois usam exatamente o mesmo conjunto.

    A empresa NÃO está aqui — ela é resolvida pelo usuário autenticado na
    view, fora do alcance de qualquer parâmetro.
    """
    params = request.query_params
    is_active = params.get("is_active")
    return {
        "search": params.get("search"),
        "sector_id": parse_int_param(params.get("sector"), param_name="sector"),
        "position_id": parse_int_param(params.get("position"), param_name="position"),
        "is_active": {"true": True, "false": False}.get(is_active),
        "hired_from": parse_date(params.get("hired_from") or ""),
        "hired_to": parse_date(params.get("hired_to") or ""),
    }


class DashboardOverviewView(APIView):
    """
    GET /api/v1/dashboard/overview/

    Estatísticas agregadas de toda a empresa: totais, médias de conclusão
    de cursos/checklist, distribuição de status e progresso por setor.
    Acesso restrito ao RH.
    """

    permission_classes = [IsRHAdmin]

    def get(self, request):
        data = services.get_dashboard_overview(company=request.user.company)
        serializer = DashboardOverviewSerializer(data)
        return Response(serializer.data)


class CollaboratorListView(APIView):
    """
    GET /api/v1/dashboard/collaborators/?search=&sector=

    Lista completa de colaboradores (sem paginação) com progresso de
    cursos e checklist. A lista completa é retornada para permitir
    ordenação e filtro no cliente. Acesso restrito ao RH.
    """

    permission_classes = [IsRHAdmin]

    def get(self, request):
        rows = services.get_collaborators_list(
            company=request.user.company, **_collaborator_filters(request)
        )
        serializer = CollaboratorStatsSerializer(rows, many=True)
        return Response(serializer.data)


class CollaboratorsExportView(APIView):
    """
    GET /api/v1/dashboard/collaborators/export/

    Exporta a lista de colaboradores (mesmos dados de CollaboratorListView)
    em CSV. Acesso restrito ao RH.
    """

    permission_classes = [IsRHAdmin]

    def get(self, request):
        rows = services.get_collaborators_list(
            company=request.user.company, **_collaborator_filters(request)
        )

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="colaboradores.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "Nome", "E-mail", "Setor", "Cargo", "Ativo", "Data de contratação", "Último acesso",
            "% Treinamentos", "% Checklist", "% Geral", "Itens atrasados",
        ])
        for row in rows:
            writer.writerow([
                row["full_name"],
                row["email"],
                row["sector_name"] or "",
                row["position_name"] or "",
                "Sim" if row["is_active"] else "Não",
                row["hire_date"] or "",
                row["last_login"] or "",
                row["courses_percent"],
                row["checklist_percent"],
                row["overall_percent"],
                row["overdue_count"],
            ])
        return response


class CollaboratorDetailView(APIView):
    """
    GET /api/v1/dashboard/collaborators/<id>/

    Detalhe de um colaborador: progresso individual de cada curso e
    item de checklist elegível ao seu setor/cargo. Acesso restrito ao RH.
    """

    permission_classes = [IsRHAdmin]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk, role="colaborador", company=request.user.company)
        data = services.get_collaborator_detail(user)
        serializer = CollaboratorDetailSerializer(data)
        return Response(serializer.data)
