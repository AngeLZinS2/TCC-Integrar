from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.query_params import parse_int_param
from apps.users.permissions import IsRHAdminOrReadOnly

from .models import ChecklistItem, ChecklistProgress
from .serializers import ChecklistItemSerializer, ChecklistProgressSerializer


class ChecklistViewSet(viewsets.ModelViewSet):
    """
    Listagem e gerenciamento de itens do checklist.
    Colaborador vê itens gerais + itens do seu setor.
    Ação 'toggle' marca/desmarca item como concluído.
    """

    queryset = ChecklistItem.objects.select_related("sector").all()
    serializer_class = ChecklistItemSerializer
    permission_classes = [IsRHAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if not user.is_authenticated or not user.company_id:
            return queryset.none()

        queryset = queryset.filter(company=user.company)

        deadline = self.request.query_params.get("deadline")
        if deadline:
            queryset = queryset.filter(deadline=deadline)

        if user.is_rh_admin:
            sector_id = parse_int_param(self.request.query_params.get("sector"), param_name="sector")
            if sector_id:
                queryset = queryset.filter(sector_id=sector_id)
            return queryset

        # Colaborador vê itens gerais ou do seu setor
        sector_filter = Q(sector__isnull=True)
        if user.sector:
            sector_filter |= Q(sector=user.sector)

        return queryset.filter(sector_filter).distinct()

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=True, methods=["post", "patch"], permission_classes=[IsAuthenticated], url_path="toggle")
    def toggle(self, request, pk=None):
        """
        POST/PATCH /checklist/<id>/toggle/
        Alterna o status de concluído do item para o colaborador autenticado.
        """
        item = self.get_object()
        progress, created = ChecklistProgress.objects.get_or_create(
            user=request.user,
            item=item,
        )

        # Se passou 'completed' no body, usa o valor explícito; caso contrário, inverte o valor atual
        if "completed" in request.data:
            completed_value = bool(request.data.get("completed"))
        else:
            completed_value = not progress.completed

        progress.completed = completed_value
        progress.completed_at = timezone.now() if completed_value else None
        progress.save()

        serializer = ChecklistProgressSerializer(progress)
        return Response(serializer.data)
