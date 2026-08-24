from django.db import models


class AuditLog(models.Model):
    """
    Registro imutável de uma ação administrativa.

    Responde "quem fez o quê, quando, sobre qual recurso" — a pergunta que
    a auditoria apontou como impossível de responder no sistema.

    Escopo: `company` nulo apenas para eventos da plataforma (ações do dono
    do sistema, que não pertence a nenhum tenant). Todo evento dentro de uma
    empresa carrega o tenant, e a listagem filtra por ele.

    Nunca armazena senha, token ou o conteúdo de campos sensíveis — apenas
    o NOME dos campos alterados, em `metadata`.
    """

    class Action(models.TextChoices):
        LOGIN = "login", "Entrou no sistema"
        LOGOUT = "logout", "Saiu do sistema"
        CREATE = "create", "Criou"
        UPDATE = "update", "Alterou"
        ACTIVATE = "activate", "Ativou"
        DEACTIVATE = "deactivate", "Desativou"
        ROLE_CHANGE = "role_change", "Alterou o papel de"
        DELETE = "delete", "Excluiu"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="Empresa",
        help_text="Nulo apenas para eventos da plataforma (dono do sistema).",
    )
    actor = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_actions",
        verbose_name="Autor",
        help_text="Nulo se o usuário for removido — o histórico permanece.",
    )
    actor_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Nome do autor",
        help_text="Cópia do nome no momento da ação, para o histórico sobreviver à remoção do usuário.",
    )
    action = models.CharField(
        max_length=20, choices=Action.choices, verbose_name="Ação", db_index=True
    )
    resource_type = models.CharField(
        max_length=50, verbose_name="Tipo do recurso", db_index=True,
        help_text="Ex.: employee, sector, position, course, company.",
    )
    resource_id = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="ID do recurso"
    )
    resource_label = models.CharField(
        max_length=200, blank=True, verbose_name="Descrição do recurso",
        help_text="Nome legível do alvo no momento da ação.",
    )
    metadata = models.JSONField(
        default=dict, blank=True, verbose_name="Detalhes",
        help_text="Apenas nomes de campos alterados. Nunca valores sensíveis.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Quando", db_index=True
    )

    class Meta:
        verbose_name = "Registro de auditoria"
        verbose_name_plural = "Registros de auditoria"
        ordering = ["-created_at"]
        indexes = [
            # A tela de histórico sempre filtra por empresa e ordena por data.
            models.Index(fields=["company", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.actor_name} {self.get_action_display()} {self.resource_label}".strip()
