import logging

from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.common.query_params import parse_int_param
from apps.common.segmentation import narrow_to_user
from apps.users import rbac

from .models import Document, DocumentAcceptance, DocumentCategory, DocumentVersion
from .serializers import (
    DocumentAcceptanceSerializer,
    DocumentCategorySerializer,
    DocumentSerializer,
    DocumentVersionUploadSerializer,
)

logger = logging.getLogger(__name__)


def _pode_gerenciar(user) -> bool:
    """Quem publica documento é quem administra materiais na empresa."""
    return user.has_perm_code(rbac.MATERIALS_CREATE)


def documentos_visiveis(user):
    """
    Documentos que `user` pode enxergar.

    Quem gerencia vê tudo, inclusive rascunho — precisa disso para publicar.
    Os demais veem apenas o que está publicado, dentro da validade e
    endereçado à unidade deles (alvo de unidade vazio = empresa inteira).
    """
    if not user.is_authenticated or not user.company_id:
        return Document.objects.none()

    queryset = Document.objects.filter(company_id=user.company_id)

    if not _pode_gerenciar(user):
        agora = timezone.now()
        queryset = queryset.filter(status=Document.Status.PUBLISHED).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=agora)
        )
        queryset = narrow_to_user(
            queryset,
            user,
            [(Document.target_units, "unit_id", "document_id", user.unit_id, "unidade")],
        )

    # `versions__created_by` e nao so `versions`: o serializer da versao le
    # `created_by.full_name`, entao parar em `versions` custa uma query por
    # documento na listagem.
    # `versions__created_by` e nao so `versions`: o serializer da versao le
    # `created_by.full_name`. E `target_units` e M2M serializado como lista
    # de ids — sem prefetch, o DRF consulta a intermediaria por linha.
    return queryset.select_related("category").prefetch_related(
        "versions__created_by", "target_units"
    )


class DocumentViewSet(viewsets.ModelViewSet):
    """
    CRUD de documentos. O arquivo entra pela ação `versions`.

    Criar o documento e enviar o arquivo são passos separados de propósito:
    é o que permite versionar sem recriar o registro, preservando o
    histórico de aceites das versões anteriores.
    """

    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = documentos_visiveis(self.request.user)
        params = self.request.query_params

        categoria = parse_int_param(params.get("category"), param_name="category")
        if categoria:
            queryset = queryset.filter(category_id=categoria)

        busca = params.get("search")
        if busca:
            queryset = queryset.filter(
                Q(title__icontains=busca) | Q(description__icontains=busca)
            )

        if params.get("required") == "true":
            queryset = queryset.filter(is_required=True)

        return queryset.order_by("-created_at")

    def get_serializer_context(self):
        contexto = super().get_serializer_context()
        # Um SELECT só para saber o que este usuário já aceitou, em vez de
        # uma consulta por documento na listagem.
        user = self.request.user
        if user.is_authenticated:
            contexto["aceitos_pelo_usuario"] = set(
                DocumentAcceptance.objects.filter(user=user).values_list(
                    "document_version_id", flat=True
                )
            )
        return contexto

    def _exigir_gestao(self):
        if not _pode_gerenciar(self.request.user):
            raise PermissionDenied("Você não tem permissão para gerenciar documentos.")

    def perform_create(self, serializer):
        self._exigir_gestao()
        documento = serializer.save(
            company=self.request.user.company, created_by=self.request.user
        )
        audit.record(
            self.request.user, AuditLog.Action.CREATE, "document",
            resource_id=documento.pk, resource_label=documento.title,
        )

    def perform_update(self, serializer):
        self._exigir_gestao()
        documento = serializer.save()
        audit.record(
            self.request.user, AuditLog.Action.UPDATE, "document",
            resource_id=documento.pk, resource_label=documento.title,
            metadata={"changed_fields": audit.changed_field_names(serializer.validated_data)},
        )

    def perform_destroy(self, instance):
        self._exigir_gestao()
        audit.record(
            self.request.user, AuditLog.Action.DELETE, "document",
            resource_id=instance.pk, resource_label=instance.title,
        )
        instance.delete()

    @action(detail=True, methods=["post"], url_path="versions")
    def upload_version(self, request, pk=None):
        """Envia uma nova versão. A anterior vira histórico, não é apagada."""
        self._exigir_gestao()
        documento = self.get_object()

        serializer = DocumentVersionUploadSerializer(
            data=request.data, context={"request": request, "document": documento}
        )
        serializer.is_valid(raise_exception=True)
        versao = serializer.save()

        audit.record(
            request.user, AuditLog.Action.CREATE, "document_version",
            resource_id=versao.pk,
            resource_label=f"{documento.title} v{versao.version_number}",
            metadata={"version": versao.version_number, "size_bytes": versao.size_bytes},
        )
        return Response(
            DocumentSerializer(documento, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        """Publica o documento. Exige ter pelo menos uma versão enviada."""
        self._exigir_gestao()
        documento = self.get_object()

        if not documento.versions.exists():
            return Response(
                {"detail": "Envie um arquivo antes de publicar o documento."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        documento.status = Document.Status.PUBLISHED
        documento.published_at = documento.published_at or timezone.now()
        documento.save(update_fields=["status", "published_at"])

        audit.record(
            request.user, AuditLog.Action.UPDATE, "document",
            resource_id=documento.pk, resource_label=documento.title,
            metadata={"action": "published"},
        )
        return Response(
            DocumentSerializer(documento, context=self.get_serializer_context()).data
        )

    @action(detail=True, methods=["get"], url_path="acceptances")
    def acceptances(self, request, pk=None):
        """Quem já aceitou — só para quem gerencia."""
        self._exigir_gestao()
        documento = self.get_object()
        registros = (
            DocumentAcceptance.objects.filter(document_version__document=documento)
            .select_related("user", "document_version")
            .order_by("-accepted_at")
        )
        pagina = self.paginate_queryset(registros)
        serializer = DocumentAcceptanceSerializer(pagina or registros, many=True)
        if pagina is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class DocumentCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or not user.company_id:
            return DocumentCategory.objects.none()
        return (
            DocumentCategory.objects.filter(company_id=user.company_id)
            .annotate(documents_count=Count("documents", distinct=True))
            .order_by("name")
        )

    def perform_create(self, serializer):
        if not _pode_gerenciar(self.request.user):
            raise PermissionDenied("Você não tem permissão para gerenciar categorias.")
        serializer.save(company=self.request.user.company)


class DocumentDownloadView(APIView):
    """
    GET /api/v1/documents/<pk>/versions/<version_id>/download/

    O arquivo NUNCA é servido por URL pública. Aqui o caminho é:
    autenticar → resolver a empresa pelo usuário → confirmar que o
    documento é dessa empresa → só então abrir o arquivo.

    Saber o id de um documento de outra empresa não ajuda: o queryset já
    exclui tudo que não é do tenant do requisitante.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, version_id):
        documento = get_object_or_404(documentos_visiveis(request.user), pk=pk)
        versao = get_object_or_404(DocumentVersion, pk=version_id, document=documento)

        if not versao.file:
            raise Http404("Arquivo não encontrado.")

        try:
            arquivo = versao.file.open("rb")
        except FileNotFoundError:
            logger.error(
                "Arquivo ausente no storage: documento=%s versao=%s",
                documento.pk, versao.pk,
            )
            raise Http404("Arquivo indisponível.")

        audit.record(
            request.user, AuditLog.Action.UPDATE, "document_download",
            resource_id=versao.pk,
            resource_label=f"{documento.title} v{versao.version_number}",
            metadata={"version": versao.version_number},
        )

        resposta = FileResponse(
            arquivo,
            content_type=versao.mime_type or "application/octet-stream",
            as_attachment=True,
            filename=versao.display_name,
        )
        # Documento corporativo não deve ficar em cache compartilhado.
        resposta["Cache-Control"] = "private, no-store"
        return resposta


class DocumentAcceptView(APIView):
    """
    POST /api/v1/documents/<pk>/versions/<version_id>/accept/

    Registra "li e estou de acordo" para uma VERSÃO específica. Publicar
    uma versão nova volta a exigir o aceite, sem apagar o anterior.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, version_id):
        documento = get_object_or_404(documentos_visiveis(request.user), pk=pk)
        versao = get_object_or_404(DocumentVersion, pk=version_id, document=documento)

        if not versao.is_active:
            return Response(
                {"detail": "Esta versão não é mais a vigente. Recarregue o documento."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        encaminhado = request.META.get("HTTP_X_FORWARDED_FOR")
        ip = encaminhado.split(",")[0].strip() if encaminhado else request.META.get("REMOTE_ADDR")

        _, criado = DocumentAcceptance.objects.get_or_create(
            document_version=versao,
            user=request.user,
            defaults={
                "ip_address": ip,
                # Truncado: o valor completo não acrescenta nada e pode ser longo.
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:400],
            },
        )
        if criado:
            audit.record(
                request.user, AuditLog.Action.UPDATE, "document_acceptance",
                resource_id=versao.pk,
                resource_label=f"{documento.title} v{versao.version_number}",
                metadata={"version": versao.version_number},
            )

        return Response({"status": "accepted", "already": not criado})


class MyPendingDocumentsView(generics.ListAPIView):
    """
    GET /api/v1/documents/pending/

    Documentos obrigatórios ainda sem aceite — o que a Home do colaborador
    precisa destacar.
    """

    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from .services import pendentes_de_aceite

        return pendentes_de_aceite(self.request.user).order_by("-created_at")

    def get_serializer_context(self):
        contexto = super().get_serializer_context()
        contexto["aceitos_pelo_usuario"] = set(
            DocumentAcceptance.objects.filter(user=self.request.user).values_list(
                "document_version_id", flat=True
            )
        )
        return contexto
