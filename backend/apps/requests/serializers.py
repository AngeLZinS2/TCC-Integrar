from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.common.tenant import TenantValidatedSerializerMixin
from apps.common.uploads import validate_upload
from apps.users.serializers import DirectoryUserSerializer

from .models import HRRequest, RequestAttachment, RequestComment, RequestHistory


class RequestAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestAttachment
        # O caminho do arquivo nunca sai daqui: o acesso é pela rota de
        # download, que valida a empresa antes de servir.
        fields = ["id", "original_name", "mime_type", "size_bytes", "uploaded_at"]
        read_only_fields = fields


class RequestHistorySerializer(serializers.ModelSerializer):
    actor_details = DirectoryUserSerializer(source="actor", read_only=True)
    action_display = serializers.CharField(source="get_action_type_display", read_only=True)

    class Meta:
        model = RequestHistory
        fields = [
            "id", "action_type", "action_display", "details",
            "created_at", "actor", "actor_details",
        ]
        read_only_fields = fields


class RequestCommentSerializer(serializers.ModelSerializer):
    author_details = DirectoryUserSerializer(source="author", read_only=True)
    attachments = RequestAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = RequestComment
        fields = [
            "id", "text", "is_internal", "created_at",
            "author", "author_details", "attachments",
        ]
        read_only_fields = ["id", "created_at", "author", "attachments"]


class HRRequestListSerializer(TenantValidatedSerializerMixin, serializers.ModelSerializer):
    requester_details = DirectoryUserSerializer(source="requester", read_only=True)
    assigned_to_details = DirectoryUserSerializer(source="assigned_to", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = HRRequest
        fields = [
            "id", "number", "category", "category_display", "subject",
            "status", "status_display", "priority", "priority_display",
            "due_at", "is_overdue", "created_at", "updated_at",
            "requester", "requester_details", "assigned_to", "assigned_to_details",
        ]
        # Status muda pela ação própria, que valida a transição e notifica.
        # Permitir PATCH direto pularia a máquina de estados.
        read_only_fields = ["id", "number", "created_at", "updated_at", "status", "due_at"]

    def validate_assigned_to(self, user):
        """
        Responsável precisa ser da mesma empresa.

        Sem esta checagem, o RH conseguia atribuir a solicitação a alguém de
        outro tenant — e o nome e o e-mail dessa pessoa apareciam no detalhe
        da solicitação para a empresa toda.
        """
        return self._check(user, "O responsável")


class HRRequestDetailSerializer(HRRequestListSerializer):
    description = serializers.CharField(read_only=True)
    history = RequestHistorySerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()

    class Meta(HRRequestListSerializer.Meta):
        fields = HRRequestListSerializer.Meta.fields + [
            "description", "history", "comments", "resolved_at", "closed_at",
        ]

    def get_comments(self, obj) -> list:
        """
        Nota interna do RH não aparece para o solicitante.

        A filtragem acontece aqui, no backend — esconder no app deixaria o
        texto viajando na resposta.
        """
        request = self.context.get("request")
        comentarios = obj.comments.all()
        if request and not request.user.manages_company:
            comentarios = [c for c in comentarios if not c.is_internal]
        return RequestCommentSerializer(
            comentarios, many=True, context=self.context
        ).data


class HRRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRRequest
        fields = [
            "id", "number", "status", "category", "subject",
            "description", "priority", "due_at", "created_at",
        ]
        read_only_fields = ["id", "number", "status", "due_at", "created_at"]


class HRRequestStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=HRRequest.Status.choices)


class TenantScopedUserField(serializers.PrimaryKeyRelatedField):
    """
    Aponta para um usuário da MESMA empresa de quem está requisitando.

    O escopo está no queryset, não numa validação depois: um id de outro
    tenant nem chega a existir para este campo, então não há como um erro
    de ordem de validação deixar passar.
    """

    def get_queryset(self):
        from apps.users.models import User

        request = self.context.get("request")
        company_id = getattr(getattr(request, "user", None), "company_id", None)
        if not company_id:
            return User.objects.none()
        return User.objects.filter(company_id=company_id, is_active=True).exclude(
            role="owner"
        )


class HRRequestAssignSerializer(serializers.Serializer):
    assigned_to = TenantScopedUserField(allow_null=True, required=False)


class CommentCreateSerializer(serializers.Serializer):
    """
    Comentário com anexos opcionais.

    Cada arquivo passa por `validate_upload` antes de tocar o disco:
    extensão na allowlist, MIME conferido pelo conteúdo e tamanho limitado.
    """

    text = serializers.CharField()
    is_internal = serializers.BooleanField(required=False, default=False)
    attachments = serializers.ListField(
        child=serializers.FileField(), required=False, allow_empty=True, max_length=5
    )

    def validate_attachments(self, arquivos):
        self._metadados = []
        for arquivo in arquivos:
            try:
                self._metadados.append(validate_upload(arquivo))
            except DjangoValidationError as exc:
                raise serializers.ValidationError(
                    f"{getattr(arquivo, 'name', 'arquivo')}: {exc.messages[0]}"
                )
        return arquivos

    def validate_is_internal(self, interno):
        """Nota interna é do RH; um colaborador não tem onde usá-la."""
        request = self.context.get("request")
        if interno and request and not request.user.manages_company:
            raise serializers.ValidationError(
                "Apenas RH ou administrador podem registrar nota interna."
            )
        return interno

    def create(self, validated_data):
        from . import services

        comentario = services.comentar(
            self.context["hr_request"],
            autor=self.context["request"].user,
            texto=validated_data["text"],
            interno=validated_data.get("is_internal", False),
        )

        for arquivo, meta in zip(
            validated_data.get("attachments", []), getattr(self, "_metadados", [])
        ):
            RequestAttachment.objects.create(
                comment=comentario,
                extension=meta["extension"],
                file=arquivo,
                original_name=meta["original_name"],
                mime_type=meta["mime_type"],
                size_bytes=meta["size"],
                checksum=meta["checksum"],
            )
        return comentario
