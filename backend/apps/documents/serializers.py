from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.common.tenant import TenantValidatedSerializerMixin
from apps.common.uploads import validate_upload

from .models import Document, DocumentAcceptance, DocumentCategory, DocumentVersion


class DocumentCategorySerializer(serializers.ModelSerializer):
    documents_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DocumentCategory
        fields = ["id", "name", "documents_count"]


class DocumentVersionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )
    accepted_by_me = serializers.SerializerMethodField()

    class Meta:
        model = DocumentVersion
        fields = [
            "id", "version_number", "original_name", "mime_type", "size_bytes",
            "change_note", "published_at", "created_by_name", "is_active",
            "accepted_by_me",
        ]
        # O caminho do arquivo nunca sai daqui: o acesso é sempre pela rota
        # de download, que valida empresa e permissão antes de servir.
        read_only_fields = fields

    def get_accepted_by_me(self, obj) -> bool:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        aceitos = self.context.get("aceitos_pelo_usuario")
        if aceitos is not None:
            return obj.id in aceitos
        return DocumentAcceptance.objects.filter(
            document_version=obj, user=request.user
        ).exists()


class DocumentSerializer(TenantValidatedSerializerMixin, serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    active_version = serializers.SerializerMethodField()
    has_accepted = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)
    pending_acceptance = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id", "title", "description", "category", "category_name",
            "is_required", "status", "published_at", "expires_at", "target_units",
            "created_at", "updated_at",
            "active_version", "has_accepted", "is_expired", "pending_acceptance",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "published_at"]

    def validate_category(self, category):
        return self._check(category, "A categoria")

    def validate_target_units(self, units):
        return self._check_many(units, "A unidade")

    def _versao_vigente(self, obj):
        # Usa o prefetch da view quando existe, para não consultar por linha.
        vigentes = [v for v in obj.versions.all() if v.is_active]
        return vigentes[0] if vigentes else None

    def get_active_version(self, obj) -> dict | None:
        versao = self._versao_vigente(obj)
        if not versao:
            return None
        return DocumentVersionSerializer(versao, context=self.context).data

    def get_has_accepted(self, obj) -> bool:
        """Aceite é por versão — publicar uma nova reabre a exigência."""
        versao = self._versao_vigente(obj)
        if not versao:
            return True  # nada publicado, nada a aceitar
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        aceitos = self.context.get("aceitos_pelo_usuario")
        if aceitos is not None:
            return versao.id in aceitos
        return DocumentAcceptance.objects.filter(
            document_version=versao, user=request.user
        ).exists()

    def get_pending_acceptance(self, obj) -> bool:
        """O que a Home do colaborador precisa destacar."""
        return bool(obj.is_required) and not self.get_has_accepted(obj)


class DocumentVersionUploadSerializer(serializers.Serializer):
    """
    Envio de uma nova versão.

    O arquivo passa por `validate_upload` antes de tocar o disco: extensão
    na allowlist, MIME conferido pelo conteúdo (não pelo cabeçalho), tamanho
    limitado e nome interno gerado.
    """

    file = serializers.FileField(write_only=True)
    change_note = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )

    def validate_file(self, arquivo):
        try:
            self._metadados = validate_upload(arquivo)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0])
        return arquivo

    @transaction.atomic
    def create(self, validated_data):
        documento = self.context["document"]
        usuario = self.context["request"].user
        meta = self._metadados

        # Trava a linha do documento para que dois uploads simultâneos não
        # gerem o mesmo version_number.
        Document.objects.select_for_update().get(pk=documento.pk)

        ultima = documento.versions.order_by("-version_number").first()
        proximo_numero = (ultima.version_number + 1) if ultima else 1

        # Só uma versão vigente por documento; as antigas ficam no histórico.
        documento.versions.filter(is_active=True).update(is_active=False)

        return DocumentVersion.objects.create(
            document=documento,
            version_number=proximo_numero,
            extension=meta["extension"],
            file=validated_data["file"],
            original_name=meta["original_name"],
            mime_type=meta["mime_type"],
            size_bytes=meta["size"],
            checksum=meta["checksum"],
            change_note=validated_data.get("change_note", ""),
            created_by=usuario,
            is_active=True,
        )


class DocumentAcceptanceSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    version_number = serializers.IntegerField(
        source="document_version.version_number", read_only=True
    )

    class Meta:
        model = DocumentAcceptance
        fields = ["id", "user", "user_name", "version_number", "accepted_at"]
        read_only_fields = fields
