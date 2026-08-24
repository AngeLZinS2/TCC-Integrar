from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.query_params import parse_int_param
from apps.common.segmentation import narrow_to_user
from apps.users.permissions import CanManageCourses

from . import quiz_services

from .models import Content, Course, CourseProgress
from .serializers import (
    ContentSerializer,
    CourseProgressSerializer,
    CourseSerializer,
)


class CourseViewSet(viewsets.ModelViewSet):
    """
    CRUD e listagem de cursos.
    Para colaboradores: lista cursos gerais (setor=None) + cursos do seu próprio setor/cargo.
    Para RH admin: lista todos os cursos (permite filtrar por ?sector= e ?position=).
    """

    queryset = (
        Course.objects
        # `target_units` e M2M serializado como lista de ids: sem prefetch,
        # uma query por curso na listagem.
        .prefetch_related("contents", "target_units")
        .select_related("sector", "position")
        .all()
    )
    serializer_class = CourseSerializer
    permission_classes = [CanManageCourses]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if not user.is_authenticated or not user.company_id:
            return queryset.none()

        queryset = queryset.filter(company=user.company)

        if user.is_rh_admin:
            sector_id = parse_int_param(self.request.query_params.get("sector"), param_name="sector")
            position_id = parse_int_param(self.request.query_params.get("position"), param_name="position")
            if sector_id:
                queryset = queryset.filter(sector_id=sector_id)
            if position_id:
                queryset = queryset.filter(position_id=position_id)
            return queryset

        # Colaborador vê cursos gerais (sem setor) OU vinculados ao seu setor
        sector_filter = Q(sector__isnull=True)
        if user.sector:
            sector_filter |= Q(sector=user.sector)

        # E quanto a cargo: sem cargo definido OU cargo do colaborador
        position_filter = Q(position__isnull=True)
        if user.position:
            position_filter |= Q(position=user.position)

        queryset = queryset.filter(sector_filter & position_filter).distinct()

        # Unidade afunila junto com setor e cargo: um treinamento marcado
        # para "TI" + "Unidade Centro" e do TI DA CENTRO. Alvo de unidade
        # vazio nao restringe nada.
        return narrow_to_user(
            queryset,
            user,
            [(Course.target_units, "unit_id", "course_id", user.unit_id, "unidade")],
        )

    def get_serializer_context(self):
        contexto = super().get_serializer_context()
        # Um SELECT para todo o progresso do usuario, em vez de dois por
        # curso (status proprio + pre-requisito) na listagem.
        user = self.request.user
        if user.is_authenticated:
            contexto["progresso_do_usuario"] = {
                p.course_id: p
                for p in CourseProgress.objects.filter(user=user)
            }
        return contexto

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    def perform_destroy(self, instance):
        if instance.progresses.exists():
            raise ValidationError(
                {"detail": "Não é possível excluir um curso que já tem colaboradores com progresso registrado."}
            )
        instance.delete()

    @action(detail=True, methods=["get", "patch"], permission_classes=[IsAuthenticated], url_path="progress")
    def progress(self, request, pk=None):
        """
        GET /courses/<id>/progress/  -> Retorna progresso do usuário no curso
        PATCH /courses/<id>/progress/ -> Atualiza status (not_started, in_progress, completed)
        """
        course = self.get_object()
        progress, _ = CourseProgress.objects.get_or_create(
            user=request.user,
            course=course,
        )

        if request.method == "PATCH":
            new_status = request.data.get("status")
            if new_status not in ["not_started", "in_progress", "completed"]:
                return Response(
                    {"status": "Status inválido. Escolha: not_started, in_progress ou completed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if new_status in ("in_progress", "completed") and course.prerequisite_id:
                prerequisite_completed = CourseProgress.objects.filter(
                    user=request.user, course_id=course.prerequisite_id, status="completed"
                ).exists()
                if not prerequisite_completed:
                    return Response(
                        {"status": "Conclua o curso pré-requisito antes de iniciar este."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Treinamento com avaliação não fecha por autodeclaração: quem
            # marca como concluído é a aprovação no quiz. Sem isto, bastaria
            # um PATCH para "concluir" um treinamento de compliance sem
            # responder nada — e o certificado perderia qualquer valor.
            if new_status == "completed" and quiz_services.exige_avaliacao(course):
                aprovado = course.quiz.attempts.filter(
                    user=request.user, passed=True
                ).exists()
                if not aprovado:
                    return Response(
                        {
                            "status": (
                                "Este treinamento exige aprovação na avaliação. "
                                "Responda o questionário para concluí-lo."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            progress.status = new_status
            progress.completed_at = timezone.now() if new_status == "completed" else None
            progress.save()

        serializer = CourseProgressSerializer(progress)
        return Response(serializer.data)


class ContentViewSet(viewsets.ModelViewSet):
    """
    CRUD de conteúdos/módulos de curso.
    """

    queryset = Content.objects.select_related("course").all()
    serializer_class = ContentSerializer
    permission_classes = [CanManageCourses]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if not user.is_authenticated or not user.company_id:
            return queryset.none()

        queryset = queryset.filter(course__company=user.company)

        course_id = parse_int_param(self.request.query_params.get("course"), param_name="course")
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset
