import logging

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.query_params import parse_int_param

from . import services
from .models import HRRequest, RequestAttachment
from .serializers import (
    CommentCreateSerializer,
    HRRequestAssignSerializer,
    HRRequestCreateSerializer,
    HRRequestDetailSerializer,
    HRRequestListSerializer,
    HRRequestStatusSerializer,
    RequestCommentSerializer,
)

logger = logging.getLogger(__name__)


class HRRequestViewSet(viewsets.ModelViewSet):
    """
    Solicitações de RH.

    O escopo vem de `services.visible_to`: RH/admin veem a fila da empresa,
    os demais veem as próprias e as atribuídas a si.
    """

    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        # Vai ate setor e cargo: `DirectoryUserSerializer` le `sector.name`
        # e `position.name`, entao parar no usuario deixa duas queries por
        # linha — 4 por solicitacao contando requester e assigned_to.
        queryset = services.visible_to(self.request.user).select_related(
            "requester__sector", "requester__position",
            "assigned_to__sector", "assigned_to__position",
        )
        if self.action == "retrieve":
            queryset = queryset.prefetch_related(
                "history__actor", "comments__author", "comments__attachments"
            )

        params = self.request.query_params

        status_filtro = params.get("status")
        if status_filtro == "open":
            # O filtro que a tela mais usa: tudo que ainda exige ação.
            queryset = queryset.exclude(
                status__in=[HRRequest.Status.COMPLETED, HRRequest.Status.CANCELLED]
            )
        elif status_filtro:
            queryset = queryset.filter(status=status_filtro)

        for campo in ("priority", "category"):
            valor = params.get(campo)
            if valor:
                queryset = queryset.filter(**{campo: valor})

        responsavel = parse_int_param(params.get("assigned_to"), param_name="assigned_to")
        if responsavel:
            queryset = queryset.filter(assigned_to_id=responsavel)

        if params.get("mine") == "true":
            queryset = queryset.filter(requester=self.request.user)

        desde = parse_date(params.get("date_from") or "")
        if desde:
            queryset = queryset.filter(created_at__date__gte=desde)
        ate = parse_date(params.get("date_to") or "")
        if ate:
            queryset = queryset.filter(created_at__date__lte=ate)

        return queryset.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return HRRequestCreateSerializer
        if self.action == "retrieve":
            return HRRequestDetailSerializer
        return HRRequestListSerializer

    def perform_create(self, serializer):
        # Empresa e solicitante vêm do usuário autenticado, nunca do corpo.
        solicitacao = services.abrir(
            company=self.request.user.company,
            requester=self.request.user,
            **serializer.validated_data,
        )
        serializer.instance = solicitacao

    @action(detail=True, methods=["patch"], url_path="status")
    def mudar_status(self, request, pk=None):
        """
        Transição de status.

        Quem administra a empresa move para qualquer estado permitido. O
        solicitante só pode cancelar a própria — não pode se auto-concluir.
        """
        solicitacao = self.get_object()
        serializer = HRRequestStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        novo = serializer.validated_data["status"]

        if not request.user.manages_company:
            if novo != HRRequest.Status.CANCELLED:
                raise PermissionDenied(
                    "Você só pode cancelar a sua própria solicitação."
                )
            if solicitacao.requester_id != request.user.id:
                raise PermissionDenied("Apenas quem abriu pode cancelar.")

        try:
            services.mudar_status(solicitacao, novo_status=novo, actor=request.user)
        except ValueError as exc:
            return Response({"status": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            HRRequestDetailSerializer(solicitacao, context={"request": request}).data
        )

    @action(detail=True, methods=["patch"], url_path="assign")
    def atribuir(self, request, pk=None):
        """Define o responsável pelo atendimento."""
        if not request.user.manages_company:
            raise PermissionDenied("Apenas RH ou administrador podem atribuir.")

        solicitacao = self.get_object()
        serializer = HRRequestAssignSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        services.atribuir(
            solicitacao,
            responsavel=serializer.validated_data.get("assigned_to"),
            actor=request.user,
        )
        return Response(
            HRRequestDetailSerializer(solicitacao, context={"request": request}).data
        )

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comentarios(self, request, pk=None):
        solicitacao = self.get_object()

        if request.method == "POST":
            serializer = CommentCreateSerializer(
                data=request.data,
                context={"request": request, "hr_request": solicitacao},
            )
            serializer.is_valid(raise_exception=True)
            comentario = serializer.save()
            return Response(
                RequestCommentSerializer(comentario, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )

        comentarios = solicitacao.comments.select_related("author").prefetch_related(
            "attachments"
        )
        if not request.user.manages_company:
            comentarios = comentarios.filter(is_internal=False)

        pagina = self.paginate_queryset(comentarios)
        serializer = RequestCommentSerializer(
            pagina if pagina is not None else comentarios,
            many=True,
            context={"request": request},
        )
        if pagina is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class RequestAttachmentDownloadView(APIView):
    """
    GET /api/v1/requests/<pk>/attachments/<attachment_id>/download/

    Mesmo caminho seguro dos documentos: a solicitação é resolvida pelo
    queryset já filtrado por empresa e por escopo de acesso, então conhecer
    o id de um anexo de outro tenant não ajuda.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, attachment_id):
        solicitacao = get_object_or_404(services.visible_to(request.user), pk=pk)
        anexo = get_object_or_404(
            RequestAttachment, pk=attachment_id, comment__request=solicitacao
        )

        # Nota interna do RH não vaza pelo anexo.
        if anexo.comment.is_internal and not request.user.manages_company:
            raise Http404("Anexo não encontrado.")

        try:
            arquivo = anexo.file.open("rb")
        except FileNotFoundError:
            logger.error("Anexo ausente no storage: %s", anexo.pk)
            raise Http404("Arquivo indisponível.")

        resposta = FileResponse(
            arquivo,
            content_type=anexo.mime_type or "application/octet-stream",
            as_attachment=True,
            filename=anexo.original_name or f"anexo-{anexo.pk}",
        )
        resposta["Cache-Control"] = "private, no-store"
        return resposta
