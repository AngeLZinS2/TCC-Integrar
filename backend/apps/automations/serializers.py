"""
Serializers das automações.

O ponto sensível é `config`: é JSONField, e um JSON livre num campo que
alimenta execução de código é justamente o que não pode existir. Cada tipo
de ação declara aqui o que aceita, e o resto é recusado.
"""

from rest_framework import serializers

from . import catalog
from .models import AutomationAction, AutomationCondition, AutomationRule, AutomationRun


class AutomationConditionSerializer(serializers.ModelSerializer):
    field_display = serializers.CharField(source="get_field_display", read_only=True)

    class Meta:
        model = AutomationCondition
        fields = ["id", "field", "field_display", "operator", "value"]
        read_only_fields = ["id"]


class AutomationActionSerializer(serializers.ModelSerializer):
    action_type_display = serializers.CharField(
        source="get_action_type_display", read_only=True
    )
    target_display = serializers.CharField(source="get_target_display", read_only=True)

    class Meta:
        model = AutomationAction
        fields = [
            "id", "action_type", "action_type_display",
            "target", "target_display", "config", "order",
        ]
        read_only_fields = ["id"]

    # Chaves aceitas por tipo de ação. Fora daqui, recusado.
    CONFIG_PERMITIDO = {
        catalog.SEND_NOTIFICATION: {"title", "message", "link"},
        catalog.SEND_EMAIL: {"title", "message", "link"},
        catalog.CREATE_ONBOARDING: {"template_id"},
        catalog.ASSIGN_TRAINING: {"course_ids"},
    }

    def validate(self, attrs):
        tipo = attrs.get("action_type", getattr(self.instance, "action_type", None))
        config = attrs.get("config", getattr(self.instance, "config", None)) or {}

        if not isinstance(config, dict):
            raise serializers.ValidationError({"config": "Deve ser um objeto."})

        permitidas = self.CONFIG_PERMITIDO.get(tipo, set())
        extras = set(config) - permitidas
        if extras:
            raise serializers.ValidationError(
                {"config": f"Campo(s) não aceito(s) para esta ação: {', '.join(sorted(extras))}."}
            )

        if tipo in {catalog.SEND_NOTIFICATION, catalog.SEND_EMAIL}:
            if not str(config.get("message", "")).strip():
                raise serializers.ValidationError(
                    {"config": "Informe a mensagem que será enviada."}
                )

        if tipo == catalog.ASSIGN_TRAINING:
            ids = config.get("course_ids")
            if not isinstance(ids, list) or not ids:
                raise serializers.ValidationError(
                    {"config": "Informe course_ids como uma lista de identificadores."}
                )
            if not all(isinstance(i, int) for i in ids):
                raise serializers.ValidationError(
                    {"config": "course_ids deve conter apenas números."}
                )

        return attrs


class AutomationRuleSerializer(serializers.ModelSerializer):
    conditions = AutomationConditionSerializer(many=True, required=False)
    actions = AutomationActionSerializer(many=True, required=False)
    trigger_event_display = serializers.CharField(
        source="get_trigger_event_display", read_only=True
    )
    run_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = AutomationRule
        fields = [
            "id", "name", "description",
            "trigger_event", "trigger_event_display", "is_active",
            "conditions", "actions", "run_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    @property
    def _company_id(self):
        request = self.context.get("request")
        return getattr(getattr(request, "user", None), "company_id", None)

    def validate_name(self, nome):
        """Duplicado precisa virar 400: `company` não está nos dados validados."""
        if not self._company_id:
            return nome
        conflito = AutomationRule.objects.filter(
            company_id=self._company_id, name__iexact=nome.strip()
        )
        if self.instance is not None:
            conflito = conflito.exclude(pk=self.instance.pk)
        if conflito.exists():
            raise serializers.ValidationError("Já existe uma automação com este nome.")
        return nome

    def validate(self, attrs):
        """
        Referências dentro de `config` precisam ser da própria empresa.

        Sem esta checagem, uma automação conseguiria aplicar o template de
        onboarding ou atribuir o treinamento de OUTRO tenant — o `config` é
        JSON e passa longe das FKs que o Django validaria sozinho.
        """
        # A exigência de ao menos uma ação mora AQUI, e não num
        # `validate_actions`: o validador de campo só roda quando o campo
        # vem no payload, então omitir `actions` criava uma regra que não
        # faz nada — e que aparece na lista como se funcionasse.
        if self.instance is None and not attrs.get("actions"):
            raise serializers.ValidationError(
                {"actions": "Configure ao menos uma ação."}
            )

        company_id = self._company_id
        if not company_id:
            return attrs

        for acao in attrs.get("actions", []):
            config = acao.get("config") or {}

            if template_id := config.get("template_id"):
                from apps.onboarding.models import OnboardingTemplate

                existe = OnboardingTemplate.objects.filter(
                    pk=template_id, company_id=company_id
                ).exists()
                if not existe:
                    raise serializers.ValidationError(
                        {"actions": "Template de onboarding não encontrado nesta empresa."}
                    )

            if ids := config.get("course_ids"):
                from apps.courses.models import Course

                encontrados = Course.objects.filter(
                    pk__in=ids, company_id=company_id
                ).count()
                if encontrados != len(set(ids)):
                    raise serializers.ValidationError(
                        {"actions": "Treinamento não encontrado nesta empresa."}
                    )

        return attrs

    def create(self, validated_data):
        condicoes = validated_data.pop("conditions", [])
        acoes = validated_data.pop("actions", [])
        regra = AutomationRule.objects.create(**validated_data)
        self._gravar_filhos(regra, condicoes, acoes)
        return regra

    def update(self, instance, validated_data):
        condicoes = validated_data.pop("conditions", None)
        acoes = validated_data.pop("actions", None)
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()

        # Substitui os conjuntos inteiros: manter condições antigas junto
        # das novas mudaria o significado da regra sem ninguém pedir.
        if condicoes is not None:
            instance.conditions.all().delete()
            AutomationCondition.objects.bulk_create(
                [AutomationCondition(rule=instance, **d) for d in condicoes]
            )
        if acoes is not None:
            instance.actions.all().delete()
            AutomationAction.objects.bulk_create(
                [AutomationAction(rule=instance, **d) for d in acoes]
            )
        return instance

    @staticmethod
    def _gravar_filhos(regra, condicoes, acoes):
        AutomationCondition.objects.bulk_create(
            [AutomationCondition(rule=regra, **d) for d in condicoes]
        )
        AutomationAction.objects.bulk_create(
            [AutomationAction(rule=regra, **d) for d in acoes]
        )


class AutomationRunSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source="rule.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = AutomationRun
        fields = [
            "id", "rule", "rule_name", "status", "status_display",
            "subject_label", "detail", "created_at",
        ]
        read_only_fields = fields
