from django.db.models import Q
from rest_framework import viewsets

from apps.common.query_params import parse_int_param
from apps.users.permissions import CanManageMaterials

from .models import Material
from .serializers import MaterialSerializer


class MaterialViewSet(viewsets.ModelViewSet):
    """
    CRUD e listagem de materiais/documentos de integração.
    Colaboradores veem materiais gerais + do seu setor.
    """

    queryset = Material.objects.select_related("sector").all()
    serializer_class = MaterialSerializer
    permission_classes = [CanManageMaterials]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if not user.is_authenticated or not user.company_id:
            return queryset.none()

        queryset = queryset.filter(company=user.company)

        if user.is_rh_admin:
            sector_id = parse_int_param(self.request.query_params.get("sector"), param_name="sector")
            if sector_id:
                queryset = queryset.filter(sector_id=sector_id)
            return queryset

        # Colaborador vê materiais gerais ou específicos de seu setor
        sector_filter = Q(sector__isnull=True)
        if user.sector:
            sector_filter |= Q(sector=user.sector)

        return queryset.filter(sector_filter).distinct()

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)
