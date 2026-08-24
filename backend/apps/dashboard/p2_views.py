"""
Endpoints dos painéis da P2.

Cada painel tem o seu próprio controle de acesso, e nenhum aceita
`company` por parâmetro: o tenant sempre sai do usuário autenticado.
"""

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users import rbac

from . import p2_services


class HRDashboardView(APIView):
    """
    GET /api/v1/dashboard/hr/

    Métricas de solicitações, documentos, treinamentos, onboarding e
    comunicação (Módulo 14).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.has_perm_code(rbac.DASHBOARD_READ) or not request.user.manages_company:
            raise PermissionDenied("Você não tem acesso ao painel de RH.")
        return Response(p2_services.painel_rh(request.user.company))


class MyHomeView(APIView):
    """
    GET /api/v1/dashboard/me/

    A Home do colaborador (Módulo 15) — o que exige ação dele.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(p2_services.home_do_colaborador(request.user))


class TeamDashboardView(APIView):
    """
    GET /api/v1/dashboard/team/

    O painel do gestor (Módulo 16), restrito à equipe dele.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not (user.is_gestor or user.is_sector_leader or user.manages_company):
            raise PermissionDenied("Você não gerencia uma equipe.")
        return Response(p2_services.painel_do_gestor(user))
