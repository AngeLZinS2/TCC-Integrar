"""
Automações: gatilho + condição opcional + ação.

Deliberadamente simples — não é um Zapier. Uma regra escuta UM evento,
opcionalmente filtra por uma condição, e executa uma lista de ações. Isso
cobre o que o RH precisa ("todo dev júnior admitido recebe o treinamento
de segurança") sem virar uma linguagem de programação num formulário.
"""

from django.conf import settings
from django.db import models

from . import catalog


class AutomationRule(models.Model):
    company = models.ForeignKey(
        "companies.Company", on_delete=models.CASCADE, related_name="automation_rules"
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")

    trigger_event = models.CharField(
        max_length=50, choices=catalog.EVENT_CHOICES, db_index=True,
        verbose_name="Quando acontecer",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_automations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Automação"
        verbose_name_plural = "Automações"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"], name="automation_nome_unico_por_empresa"
            )
        ]
        indexes = [models.Index(fields=["company", "trigger_event", "is_active"])]

    def __str__(self):
        return f"{self.name} ({self.get_trigger_event_display()})"


class AutomationCondition(models.Model):
    """
    Filtro opcional do gatilho.

    Várias condições numa regra valem em E: "setor = TI" + "cargo = Júnior"
    é o júnior DO TI. Somar seria surpreendente — quem escreve duas
    condições está estreitando, não ampliando.

    `value` é texto mesmo quando compara id: o formulário manda string, e
    converter na hora da comparação evita uma coluna por tipo.
    """

    rule = models.ForeignKey(
        AutomationRule, on_delete=models.CASCADE, related_name="conditions"
    )
    field = models.CharField(max_length=40, choices=catalog.CONDITION_FIELD_CHOICES)
    operator = models.CharField(
        max_length=5, choices=catalog.OPERATOR_CHOICES, default=catalog.OP_EQUALS
    )
    value = models.CharField(
        max_length=255, help_text="Para 'está entre', separe por vírgula."
    )

    class Meta:
        verbose_name = "Condição"
        verbose_name_plural = "Condições"
        ordering = ["id"]

    def __str__(self):
        return f"{self.field} {self.operator} {self.value}"

    def matches(self, contexto: dict) -> bool:
        atual = contexto.get(self.field)
        esperados = [v.strip() for v in self.value.split(",") if v.strip()]
        # Comparação como texto dos dois lados: o contexto traz int (id) e a
        # regra guarda string. Normalizar aqui evita "5" != 5 passar
        # despercebido e a automação nunca disparar.
        atual_txt = "" if atual is None else str(atual)

        if self.operator == catalog.OP_EQUALS:
            return atual_txt == (esperados[0] if esperados else "")
        if self.operator == catalog.OP_NOT_EQUALS:
            return atual_txt != (esperados[0] if esperados else "")
        if self.operator == catalog.OP_IN:
            return atual_txt in esperados
        return False


class AutomationAction(models.Model):
    """
    O que a regra faz.

    `config` é JSON porque cada ação precisa de parâmetros diferentes
    (a mensagem da notificação, o id do treinamento). O formato aceito de
    cada uma está documentado em `actions.py`, e é validado no serializer —
    JSON livre aqui seria um campo que ninguém consegue conferir.
    """

    rule = models.ForeignKey(
        AutomationRule, on_delete=models.CASCADE, related_name="actions"
    )
    action_type = models.CharField(max_length=40, choices=catalog.ACTION_CHOICES)
    target = models.CharField(
        max_length=20, choices=catalog.TARGET_CHOICES, default=catalog.TARGET_EMPLOYEE
    )
    config = models.JSONField(default=dict, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Ação"
        verbose_name_plural = "Ações"
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.get_action_type_display()} → {self.get_target_display()}"


class AutomationRun(models.Model):
    """
    Registro de cada disparo.

    Sem isto, uma automação que falha em silêncio é indistinguível de uma
    que nunca foi acionada — e quem configurou não tem como descobrir qual
    das duas aconteceu.
    """

    class Status(models.TextChoices):
        SUCCESS = "success", "Executada"
        SKIPPED = "skipped", "Ignorada (condição não bateu)"
        FAILED = "failed", "Falhou"

    rule = models.ForeignKey(
        AutomationRule, on_delete=models.CASCADE, related_name="runs"
    )
    company = models.ForeignKey(
        "companies.Company", on_delete=models.CASCADE, related_name="automation_runs"
    )
    status = models.CharField(max_length=10, choices=Status.choices, db_index=True)
    subject_label = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Sobre quem/o quê o disparo aconteceu.",
    )
    detail = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Execução de automação"
        verbose_name_plural = "Execuções de automação"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["company", "-created_at"])]

    def __str__(self):
        return f"{self.rule.name} — {self.get_status_display()}"
