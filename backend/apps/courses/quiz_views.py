"""
Endpoints da avaliação e dos certificados.
"""

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.users import rbac

from . import quiz_services
from .models import Course
from .quiz_models import Certificate, Question, Quiz, QuizAttempt
from .quiz_serializers import (
    CertificateSerializer,
    PublicCertificateSerializer,
    QuestionAdminSerializer,
    QuizAdminSerializer,
    QuizAttemptResultSerializer,
    QuizAttemptSerializer,
    QuizForTakingSerializer,
    SubmitAnswersSerializer,
)


def cursos_da_empresa(user):
    if not user.is_authenticated or not user.company_id:
        return Course.objects.none()
    return Course.objects.filter(company_id=user.company_id)


def _pode_gerenciar(user, curso) -> bool:
    """
    Monta avaliação quem pode criar treinamento — e, no caso do líder de
    setor, só do próprio setor.
    """
    if not user.has_perm_code(rbac.TRAINING_CREATE):
        return False
    if user.manages_company:
        return True
    return curso.sector_id is not None and curso.sector_id == user.sector_id


class CourseQuizView(APIView):
    """
    GET/PUT/DELETE /api/v1/courses/<course_id>/quiz/

    O GET devolve a versão SEM gabarito para quem vai responder, e a versão
    com gabarito para quem administra o treinamento.
    """

    permission_classes = [permissions.IsAuthenticated]

    def _curso(self, request, course_id):
        return get_object_or_404(cursos_da_empresa(request.user), pk=course_id)

    def get(self, request, course_id):
        curso = self._curso(request, course_id)
        quiz = getattr(curso, "quiz", None)
        if quiz is None:
            return Response({"detail": "Este treinamento não tem avaliação."}, status=404)

        if _pode_gerenciar(request.user, curso):
            serializer = QuizAdminSerializer(quiz, context={"request": request})
        else:
            serializer = QuizForTakingSerializer(quiz, context={"request": request})
        return Response(serializer.data)

    def put(self, request, course_id):
        """Cria ou atualiza a avaliação do treinamento."""
        curso = self._curso(request, course_id)
        if not _pode_gerenciar(request.user, curso):
            raise PermissionDenied("Você não pode editar a avaliação deste treinamento.")

        quiz = getattr(curso, "quiz", None)
        serializer = QuizAdminSerializer(
            quiz, data=request.data, partial=bool(quiz), context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        quiz = serializer.save(course=curso)

        audit.record(
            request.user, AuditLog.Action.UPDATE, "quiz",
            resource_id=quiz.pk, resource_label=curso.title,
        )
        return Response(QuizAdminSerializer(quiz, context={"request": request}).data)

    def delete(self, request, course_id):
        curso = self._curso(request, course_id)
        if not _pode_gerenciar(request.user, curso):
            raise PermissionDenied("Você não pode remover a avaliação deste treinamento.")

        quiz = getattr(curso, "quiz", None)
        if quiz is None:
            return Response(status=status.HTTP_204_NO_CONTENT)

        audit.record(
            request.user, AuditLog.Action.DELETE, "quiz",
            resource_id=quiz.pk, resource_label=curso.title,
        )
        quiz.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class QuizQuestionViewSet(viewsets.ModelViewSet):
    """
    CRUD das perguntas. Sempre com gabarito — só quem administra chega aqui.
    """

    serializer_class = QuestionAdminSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _quiz(self):
        curso = get_object_or_404(
            cursos_da_empresa(self.request.user), pk=self.kwargs["course_id"]
        )
        if not _pode_gerenciar(self.request.user, curso):
            raise PermissionDenied("Você não pode editar a avaliação deste treinamento.")
        return get_object_or_404(Quiz, course=curso)

    def get_queryset(self):
        # Escopo pelo curso da própria empresa: um question_id de outro
        # tenant não é alcançável.
        curso_id = self.kwargs["course_id"]
        return Question.objects.filter(
            quiz__course__company_id=self.request.user.company_id,
            quiz__course_id=curso_id,
        ).prefetch_related("options")

    def perform_create(self, serializer):
        serializer.save(quiz=self._quiz())

    def perform_update(self, serializer):
        self._quiz()
        serializer.save()

    def perform_destroy(self, instance):
        self._quiz()
        instance.delete()


class QuizAttemptView(APIView):
    """
    POST /api/v1/courses/<course_id>/quiz/attempts/   → inicia tentativa
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, course_id):
        curso = get_object_or_404(cursos_da_empresa(request.user), pk=course_id)
        quiz = get_object_or_404(Quiz, course=curso)

        try:
            tentativa = quiz_services.iniciar_tentativa(quiz, request.user)
        except quiz_services.QuizError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "attempt": QuizAttemptSerializer(tentativa).data,
                "quiz": QuizForTakingSerializer(quiz, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class QuizSubmitView(APIView):
    """
    POST /api/v1/courses/<course_id>/quiz/attempts/<attempt_id>/submit/

    Corrige no servidor e devolve nota e veredito — nunca o gabarito.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, course_id, attempt_id):
        curso = get_object_or_404(cursos_da_empresa(request.user), pk=course_id)
        # Filtrado por `user`: ninguém envia respostas na tentativa de outro.
        tentativa = get_object_or_404(
            QuizAttempt, pk=attempt_id, user=request.user, quiz__course=curso
        )

        serializer = SubmitAnswersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            tentativa = quiz_services.enviar_respostas(
                tentativa, serializer.validated_data["answers"]
            )
        except quiz_services.QuizError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(QuizAttemptResultSerializer(tentativa).data)


class MyAttemptsView(generics.ListAPIView):
    """Histórico de tentativas do próprio usuário."""

    serializer_class = QuizAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            QuizAttempt.objects.filter(
                user=self.request.user,
                quiz__course__company_id=self.request.user.company_id,
            )
            .select_related("quiz__course")
            .order_by("-started_at")
        )


class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Certificados. Somente leitura: emitir é consequência de ser aprovado,
    não uma ação que alguém dispara.
    """

    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "code"

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.company_id:
            return Certificate.objects.none()

        queryset = Certificate.objects.filter(
            company_id=user.company_id
        ).select_related("user", "course", "company")

        # RH vê os da empresa para conferir compliance; os demais, só os
        # próprios.
        if not user.manages_company:
            queryset = queryset.filter(user=user)
        return queryset.order_by("-issued_at")


class CertificateValidationView(APIView):
    """
    GET /api/v1/certificates/validate/<code>/

    Rota PÚBLICA: um certificado serve para ser conferido por quem está
    fora do sistema — o RH de outra empresa, por exemplo. Devolve só o
    necessário para confirmar autenticidade (ver PublicCertificateSerializer).
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, code):
        certificado = Certificate.objects.filter(code=code.upper().strip()).select_related(
            "user", "course", "company"
        ).first()

        if certificado is None:
            return Response(
                {"valid": False, "detail": "Certificado não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {"valid": True, "certificate": PublicCertificateSerializer(certificado).data}
        )
