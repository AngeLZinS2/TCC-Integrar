from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "actor_name",
            "action",
            "action_display",
            "resource_type",
            "resource_id",
            "resource_label",
            "summary",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields

    # Recursos cuja ação já se explica sozinha — "entrou no sistema" não
    # precisa de complemento, e citar o tipo interno soaria como vazamento
    # de jargão técnico na tela.
    _SELF_EXPLANATORY = frozenset({"session"})

    _ARTICLES = {
        "employee": "o colaborador",
        "sector": "o setor",
        "position": "o cargo",
        "company": "os dados da empresa",
        "course": "o treinamento",
        "material": "o material",
    }

    def get_summary(self, obj) -> str:
        """Frase pronta para a tela: 'Fulano alterou o colaborador Beltrano'."""
        autor = obj.actor_name or "Usuário removido"
        verbo = obj.get_action_display().lower()

        if obj.resource_type in self._SELF_EXPLANATORY:
            return f"{autor} {verbo}"

        artigo = self._ARTICLES.get(obj.resource_type, "")
        alvo = obj.resource_label or obj.resource_type
        return " ".join(p for p in (autor, verbo, artigo, alvo) if p)
