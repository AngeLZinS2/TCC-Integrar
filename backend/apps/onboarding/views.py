"""
Endpoints das tarefas e dos templates de onboarding.
"""

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.common.uploads import validate_upload
from apps.users import rbac
from apps.users.scopes import managed_users_filter

from . import services
from .models import (
    OnboardingTask,
    OnboardingTaskAttachment,
    OnboardingTaskComment,
    OnboardingTemplate,
)
from .serializers import (
    ApplyTemplateSerializer,
    CommentCreateSerializer,
    OnboardingTaskAttachmentSerializer,
    OnboardingTaskCommentSerializer,
    OnboardingTaskDetailSerializer,
    OnboardingTaskSerializer,
    OnboardingTemplateSerializer,
    TaskStatusSerializer,
)


def tarefas_visiveis(user):
    """
    Quais tarefas cada papel enxerga.

    O colaborador vê a própria integração e o que lhe foi atribuído — nunca
    o plano de integração dos colegas, que revelaria admissão, cargo e
    pendências deles.
    """
    if not user.is_authenticated or not user.company_id:
        return OnboardingTask.objects.none()

    queryset = OnboardingTask.objects.filter(company_id=user.company_id)

    if user.has_perm_code(rbac.ONBOARDING_MANAGE):
        return queryset

    if user.is_gestor or user.is_sector_leader:
        # Equipe do gestor + o que ele mesmo precisa executar.
        from apps.users.models import User

        equipe = User.objects.filter(
            company_id=user.company_id
        ).filter(managed_users_filter(user)).values("pk")
        return queryset.filter(
            Q(employee__in=equipe) | Q(assigned_to=user) | Q(employee=user)
        )

    return queryset.filter(Q(employee=user) | Q(assigned_to=user))


class OnboardingTaskViewSet(viewsets.ModelViewSet):
    """
    /api/v1/onboarding/tasks/

    Criar, editar e excluir exigem `onboarding.manage`. Mudar o status não:
    quem executa a tarefa fecha a tarefa, e isso vai pela ação `status`.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = (
            tarefas_visiveis(self.request.user)
            .select_related("employee__position", "assigned_to__position")
            .annotate(
                comment_count=Count("comments", distinct=True),
                attachment_count=Count("attachments", distinct=True),
            )
            # Explicito: com o GROUP BY do annotate, o ordering do Meta se
            # perde e a paginacao passa a devolver a mesma tarefa em duas
            # paginas diferentes.
            .order_by("due_date", "order", "id")
        )

        params = self.request.query_params
        if valor := params.get("status"):
            queryset = queryset.filter(status=valor)
        if valor := params.get("employee"):
            queryset = queryset.filter(employee_id=valor)
        if valor := params.get("assigned_to"):
            queryset = queryset.filter(assigned_to_id=valor)
        if params.get("mine") in {"1", "true", "True"}:
            queryset = queryset.filter(assigned_to=self.request.user)
        if params.get("overdue") in {"1", "true", "True"}:
            from django.utils import timezone

            queryset = queryset.filter(
                due_date__lt=timezone.localdate(),
                status__in=[OnboardingTask.Status.PENDING, OnboardingTask.Status.IN_PROGRESS],
            )
        return queryset

    def get_serializer_class(self):
        if self.action in {"retrieve", "create", "update", "partial_update"}:
            return OnboardingTaskDetailSerializer
        return OnboardingTaskSerializer

    def _exigir_gestao(self):
        """
        Checado ANTES da validação do corpo.

        Se rodasse depois, quem não tem permissão receberia 400 com o
        formato esperado do payload — um 403 que ensina a montar a
        requisição.
        """
        if not self.request.user.has_perm_code(rbac.ONBOARDING_MANAGE):
            raise PermissionDenied("Você não pode gerenciar tarefas de onboarding.")

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
        tarefa = serializer.save(
            company_id=self.request.user.company_id, created_by=self.request.user
        )
        audit.record(
            self.request.user, AuditLog.Action.CREATE, "onboarding_task",
            resource_id=tarefa.pk, resource_label=tarefa.title,
        )

    @action(detail=True, methods=["post"], url_path="status")
    def mudar_status(self, request, pk=None):
        tarefa = self.get_object()
        serializer = TaskStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            tarefa = services.mudar_status(
                tarefa, serializer.validated_data["status"], request.user
            )
        except services.OnboardingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

        atualizada = self.get_queryset().get(pk=tarefa.pk)
        return Response(
            OnboardingTaskSerializer(atualizada, context={"request": request}).data
        )

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comentarios(self, request, pk=None):
        tarefa = self.get_object()

        if request.method == "GET":
            comentarios = tarefa.comments.select_related("author")
            if not request.user.has_perm_code(rbac.ONBOARDING_MANAGE):
                comentarios = comentarios.filter(is_internal=False)
            return Response(
                OnboardingTaskCommentSerializer(comentarios, many=True).data
            )

        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        interno = serializer.validated_data["is_internal"]
        if interno and not request.user.has_perm_code(rbac.ONBOARDING_MANAGE):
            # Sem isto, o colaborador marcaria o próprio comentário como
            # interno e ele sumiria da tela dele — e do histórico que ele
            # deveria poder consultar.
            interno = False

        comentario = OnboardingTaskComment.objects.create(
            task=tarefa,
            author=request.user,
            message=serializer.validated_data["message"],
            is_internal=interno,
        )
        return Response(
            OnboardingTaskCommentSerializer(comentario).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True, methods=["post"], url_path="attachments",
        parser_classes=[MultiPartParser, FormParser],
    )
    def anexar(self, request, pk=None):
        tarefa = self.get_object()

        arquivo = request.FILES.get("file")
        if not arquivo:
            return Response(
                {"file": "Envie um arquivo."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            dados = validate_upload(arquivo)
        except Exception as exc:  # ValidationError do uploads
            return Response({"file": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        anexo = OnboardingTaskAttachment(
            task=tarefa,
            original_name=dados["original_name"],
            extension=dados["extension"],
            mime_type=dados["mime_type"],
            size_bytes=dados["size"],
            checksum=dados["checksum"],
            uploaded_by=request.user,
        )
        anexo.file = arquivo
        anexo.save()

        audit.record(
            request.user, AuditLog.Action.CREATE, "onboarding_attachment",
            resource_id=anexo.pk, resource_label=anexo.original_name,
        )
        return Response(
            OnboardingTaskAttachmentSerializer(anexo).data,
            status=status.HTTP_201_CREATED,
        )


class MyOnboardingView(APIView):
    """
    /api/v1/onboarding/my/

    A tela de integração do próprio colaborador: o que ele precisa fazer,
    com o percentual concluído.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        tarefas = (
            OnboardingTask.objects.filter(employee=request.user)
            .exclude(status=OnboardingTask.Status.CANCELLED)
            .select_related("assigned_to__position", "employee__position")
        )
        return Response(
            {
                "progress": services.progresso_de(request.user),
                "tasks": OnboardingTaskSerializer(
                    tarefas, many=True, context={"request": request}
                ).data,
            }
        )


class EmployeeOnboardingView(APIView):
    """
    /api/v1/onboarding/employees/<id>/

    Acompanhamento da integração de um colaborador pelo RH ou pelo gestor.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, employee_id):
        from apps.users.models import User
        from apps.users.scopes import can_view_colaborador

        colaborador = get_object_or_404(
            User.objects.filter(company_id=request.user.company_id), pk=employee_id
        )
        if not can_view_colaborador(request.user, colaborador):
            raise PermissionDenied("Você não acompanha a integração deste colaborador.")

        tarefas = (
            OnboardingTask.objects.filter(employee=colaborador)
            .select_related("assigned_to__position", "employee__position")
        )
        return Response(
            {
                "employee": {"id": colaborador.pk, "full_name": colaborador.full_name},
                "progress": services.progresso_de(colaborador),
                "tasks": OnboardingTaskSerializer(
                    tarefas, many=True, context={"request": request}
                ).data,
            }
        )


class OnboardingTemplateViewSet(viewsets.ModelViewSet):
    """
    /api/v1/onboarding/templates/

    Só quem administra a integração mexe em template — um roteiro errado se
    replica para todo mundo que for admitido depois.
    """

    serializer_class = OnboardingTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.company_id:
            return OnboardingTemplate.objects.none()
        return (
            OnboardingTemplate.objects.filter(company_id=user.company_id)
            .select_related("sector", "position")
            .prefetch_related("tasks")
            .annotate(task_count=Count("tasks", distinct=True))
            # Explicito: o GROUP BY do annotate descarta o ordering do Meta,
            # e sem ordem a paginacao pode repetir um template entre paginas.
            .order_by("name")
        )

    def _exigir_gestao(self):
        if not self.request.user.has_perm_code(rbac.ONBOARDING_MANAGE):
            raise PermissionDenied("Você não pode gerenciar templates de onboarding.")

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
        template = serializer.save(
            company_id=self.request.user.company_id, created_by=self.request.user
        )
        audit.record(
            self.request.user, AuditLog.Action.CREATE, "onboarding_template",
            resource_id=template.pk, resource_label=template.name,
        )

    @action(detail=True, methods=["post"], url_path="apply")
    def aplicar(self, request, pk=None):
        """Aplica o roteiro a um colaborador já cadastrado."""
        self._exigir_gestao()
        template = self.get_object()

        serializer = ApplyTemplateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        try:
            criadas = services.aplicar_template(
                template, serializer.validated_data["employee"], criado_por=request.user
            )
        except services.OnboardingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "created": len(criadas),
                "detail": (
                    f"{len(criadas)} tarefa(s) criadas."
                    if criadas
                    else "Este colaborador já tinha as tarefas deste template."
                ),
            },
            status=status.HTTP_201_CREATED if criadas else status.HTTP_200_OK,
        )
