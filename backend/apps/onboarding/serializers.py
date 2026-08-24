"""
Serializers do onboarding.

Todo campo que aponta para outra pessoa passa por `TenantScopedUserField`:
o escopo mora no queryset, não numa validação posterior, então um id de
outra empresa nem chega a existir para o campo.
"""

from rest_framework import serializers

from apps.common.tenant import TenantValidatedSerializerMixin

from .models import (
    OnboardingTask,
    OnboardingTaskAttachment,
    OnboardingTaskComment,
    OnboardingTemplate,
    TemplateTask,
)


class TenantScopedUserField(serializers.PrimaryKeyRelatedField):
    """Usuário da MESMA empresa de quem está requisitando."""

    def get_queryset(self):
        from apps.users.models import User

        request = self.context.get("request")
        company_id = getattr(getattr(request, "user", None), "company_id", None)
        if not company_id:
            return User.objects.none()
        return User.objects.filter(company_id=company_id, is_active=True).exclude(
            role="owner"
        )


class PessoaResumoSerializer(serializers.Serializer):
    """
    Identificação mínima de quem aparece numa tarefa.

    Nome e cargo bastam para saber com quem falar; e-mail, telefone e setor
    ficam de fora — a tarefa não é o lugar de expor a ficha de ninguém.
    """

    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    position_name = serializers.CharField(source="position.name", read_only=True, default=None)


class OnboardingTaskCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)

    class Meta:
        model = OnboardingTaskComment
        fields = ["id", "message", "is_internal", "author_name", "created_at"]
        read_only_fields = ["id", "author_name", "created_at"]


class OnboardingTaskAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(
        source="uploaded_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = OnboardingTaskAttachment
        fields = [
            "id", "original_name", "extension", "mime_type", "size_bytes",
            "uploaded_by_name", "uploaded_at",
        ]
        read_only_fields = fields


class OnboardingTaskSerializer(TenantValidatedSerializerMixin, serializers.ModelSerializer):
    employee = TenantScopedUserField()
    assigned_to = TenantScopedUserField(allow_null=True, required=False)

    employee_detail = PessoaResumoSerializer(source="employee", read_only=True)
    assigned_to_detail = PessoaResumoSerializer(source="assigned_to", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_late = serializers.IntegerField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True, required=False)
    attachment_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = OnboardingTask
        fields = [
            "id", "title", "description",
            "employee", "employee_detail", "assigned_to", "assigned_to_detail",
            "due_date", "priority", "priority_display",
            "status", "status_display", "order",
            "is_overdue", "days_late",
            "comment_count", "attachment_count",
            "created_at", "completed_at",
        ]
        read_only_fields = ["id", "created_at", "completed_at", "status"]


class OnboardingTaskDetailSerializer(OnboardingTaskSerializer):
    comments = serializers.SerializerMethodField()
    attachments = OnboardingTaskAttachmentSerializer(many=True, read_only=True)

    class Meta(OnboardingTaskSerializer.Meta):
        fields = OnboardingTaskSerializer.Meta.fields + ["comments", "attachments"]

    def get_comments(self, obj) -> list:
        """
        Comentário interno não sai para o colaborador integrado.

        A filtragem é aqui e não no queryset porque o mesmo objeto é servido
        para os dois públicos — o RH precisa ver tudo na mesma tela.
        """
        from apps.users import rbac

        request = self.context.get("request")
        user = getattr(request, "user", None)
        comentarios = obj.comments.select_related("author")

        pode_ver_interno = bool(
            user and user.is_authenticated and user.has_perm_code(rbac.ONBOARDING_MANAGE)
        )
        if not pode_ver_interno:
            comentarios = comentarios.filter(is_internal=False)
        return OnboardingTaskCommentSerializer(comentarios, many=True).data


class TaskStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OnboardingTask.Status.choices)


class CommentCreateSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=5000)
    is_internal = serializers.BooleanField(required=False, default=False)


# ── Templates ───────────────────────────────────────────────────────────────

class TemplateTaskSerializer(serializers.ModelSerializer):
    responsible_display = serializers.CharField(
        source="get_responsible_display", read_only=True
    )

    class Meta:
        model = TemplateTask
        fields = [
            "id", "title", "description", "days_offset",
            "responsible", "responsible_display", "priority", "order",
        ]
        read_only_fields = ["id"]


class OnboardingTemplateSerializer(
    TenantValidatedSerializerMixin, serializers.ModelSerializer
):
    tasks = TemplateTaskSerializer(many=True, required=False)
    sector_name = serializers.CharField(source="sector.name", read_only=True, default=None)
    position_name = serializers.CharField(
        source="position.name", read_only=True, default=None
    )
    task_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = OnboardingTemplate
        fields = [
            "id", "name", "description",
            "sector", "sector_name", "position", "position_name",
            "is_active", "apply_automatically",
            "tasks", "task_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, nome):
        """
        Nome duplicado precisa virar 400, não 500.

        A UniqueConstraint é (company, name), mas `company` é injetada no
        `perform_create` e não está nos dados validados — então o
        UniqueTogetherValidator do DRF não consegue montar a checagem
        sozinho, e o duplicado ia estourar IntegrityError na hora do INSERT.
        """
        actor = self._actor
        company_id = getattr(actor, "company_id", None)
        if not company_id:
            return nome

        conflito = OnboardingTemplate.objects.filter(
            company_id=company_id, name__iexact=nome.strip()
        )
        if self.instance is not None:
            conflito = conflito.exclude(pk=self.instance.pk)
        if conflito.exists():
            raise serializers.ValidationError("Já existe um template com este nome.")
        return nome

    def validate_sector(self, sector):
        return self._check(sector, "Setor")

    def validate_position(self, position):
        return self._check(position, "Cargo")

    def validate(self, attrs):
        sector = attrs.get("sector", getattr(self.instance, "sector", None))
        position = attrs.get("position", getattr(self.instance, "position", None))
        if position and sector and position.sector_id != sector.id:
            raise serializers.ValidationError(
                {"position": "O cargo não pertence ao setor escolhido."}
            )
        return attrs

    def create(self, validated_data):
        tarefas = validated_data.pop("tasks", [])
        template = OnboardingTemplate.objects.create(**validated_data)
        self._gravar_tarefas(template, tarefas)
        return template

    def update(self, instance, validated_data):
        tarefas = validated_data.pop("tasks", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()

        if tarefas is not None:
            # Substitui o roteiro inteiro. As tarefas JÁ GERADAS a partir
            # dele não são tocadas: mudar o template não pode reescrever
            # retroativamente a integração de quem já começou.
            instance.tasks.all().delete()
            self._gravar_tarefas(instance, tarefas)
        return instance

    @staticmethod
    def _gravar_tarefas(template, tarefas):
        TemplateTask.objects.bulk_create(
            [TemplateTask(template=template, **dados) for dados in tarefas]
        )


class ApplyTemplateSerializer(serializers.Serializer):
    employee = TenantScopedUserField()
