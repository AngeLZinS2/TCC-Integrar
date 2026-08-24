"""
Tarefas de integração de um colaborador.

Evolução do checklist (`apps.checklist`). O checklist era uma lista da
empresa com um "concluído" por pessoa: servia para o colaborador se
orientar, mas não respondia quem tinha que fazer o quê nem até quando.

Aqui cada tarefa é uma linha própria, com responsável e data. É essa
diferença que permite cobrar: "Criar acessos" é do RH, "Apresentar a
equipe" é do gestor, "Enviar RG" é do colaborador — e o atraso de cada uma
tem dono.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.uploads import build_storage_path


def onboarding_attachment_path(instance, filename):
    """
    Anexo de tarefa, particionado por empresa.

    O nome enviado é descartado — o caminho final é gerado internamente,
    o que fecha path traversal e evita que o nome do arquivo exponha o
    conteúdo no storage.
    """
    return build_storage_path(
        company_id=instance.task.company_id,
        scope="onboarding_attachments",
        extension=instance.extension or "bin",
    )


class OnboardingTask(models.Model):
    """
    Uma tarefa da integração de um colaborador.

    `employee` é de quem é a integração; `assigned_to` é quem precisa
    executar. Quase sempre são pessoas diferentes — confundir os dois foi
    o que o checklist antigo não conseguia representar.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        IN_PROGRESS = "in_progress", "Em andamento"
        COMPLETED = "completed", "Concluída"
        CANCELLED = "cancelled", "Cancelada"

    class Priority(models.TextChoices):
        LOW = "low", "Baixa"
        NORMAL = "normal", "Normal"
        HIGH = "high", "Alta"
        URGENT = "urgent", "Urgente"

    company = models.ForeignKey(
        "companies.Company", on_delete=models.CASCADE, related_name="onboarding_tasks"
    )
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="onboarding_tasks",
        verbose_name="Colaborador integrado",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_onboarding_tasks",
        verbose_name="Responsável",
        help_text="Quem executa a tarefa. Vazio = ainda sem responsável.",
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")

    due_date = models.DateField(
        null=True, blank=True, help_text="Prazo. Vazio = tarefa sem data."
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.NORMAL
    )
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    order = models.PositiveIntegerField(default=0)

    template_task = models.ForeignKey(
        "onboarding.TemplateTask",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_tasks",
        help_text="Origem, quando a tarefa veio de um template.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_onboarding_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_onboarding_tasks",
    )

    class Meta:
        verbose_name = "Tarefa de onboarding"
        verbose_name_plural = "Tarefas de onboarding"
        ordering = ["due_date", "order", "id"]
        indexes = [
            models.Index(fields=["company", "employee", "status"]),
            models.Index(fields=["company", "assigned_to", "status"]),
            models.Index(fields=["company", "due_date"]),
        ]

    def __str__(self):
        return f"{self.title} — {self.employee.full_name}"

    @property
    def is_open(self) -> bool:
        return self.status in {self.Status.PENDING, self.Status.IN_PROGRESS}

    @property
    def is_overdue(self) -> bool:
        """
        Atrasada é estado DERIVADO, não um valor salvo em `status`.

        O spec lista "overdue" junto dos outros status, mas gravá-lo exigiria
        uma rotina varrendo a tabela à meia-noite para continuar verdadeiro —
        e qualquer falha dela deixaria o painel mentindo. Calculado, o atraso
        nunca fica velho.
        """
        return bool(
            self.due_date and self.is_open and self.due_date < timezone.localdate()
        )

    @property
    def days_late(self) -> int:
        if not self.is_overdue:
            return 0
        return (timezone.localdate() - self.due_date).days


class OnboardingTaskComment(models.Model):
    """
    Andamento da tarefa.

    `is_internal` esconde o comentário do colaborador integrado: o RH
    precisa registrar "documento veio ilegível, cobrar de novo" sem que
    isso apareça para ele.
    """

    task = models.ForeignKey(
        OnboardingTask, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="onboarding_comments"
    )
    message = models.TextField()
    is_internal = models.BooleanField(
        default=False, help_text="Visível apenas para RH e gestão."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Comentário da tarefa"
        verbose_name_plural = "Comentários da tarefa"

    def __str__(self):
        return f"{self.author} → {self.task_id}"


class OnboardingTaskAttachment(models.Model):
    """Arquivo entregue na tarefa — o RG pedido, o termo assinado."""

    task = models.ForeignKey(
        OnboardingTask, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to=onboarding_attachment_path)
    original_name = models.CharField(max_length=255)
    extension = models.CharField(max_length=10, default="")
    mime_type = models.CharField(max_length=100, default="")
    size_bytes = models.PositiveIntegerField(default=0)
    checksum = models.CharField(max_length=64, default="", db_index=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="onboarding_uploads",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Anexo da tarefa"
        verbose_name_plural = "Anexos da tarefa"

    def __str__(self):
        return self.original_name


# ── Templates ───────────────────────────────────────────────────────────────

class OnboardingTemplate(models.Model):
    """
    Roteiro de integração reaproveitável.

    Um template descreve a integração de um TIPO de vaga ("Desenvolvedor
    Júnior"), não de uma pessoa. Ao cadastrar o colaborador, ele vira
    tarefas com datas reais.
    """

    company = models.ForeignKey(
        "companies.Company", on_delete=models.CASCADE, related_name="onboarding_templates"
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")

    sector = models.ForeignKey(
        "sectors.Sector",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_templates",
        help_text="Vazio = vale para qualquer setor.",
    )
    position = models.ForeignKey(
        "sectors.Position",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_templates",
        help_text="Vazio = vale para qualquer cargo do setor.",
    )

    is_active = models.BooleanField(default=True)
    apply_automatically = models.BooleanField(
        default=True,
        help_text="Aplica sozinho ao cadastrar um colaborador que se encaixe.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_onboarding_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Template de onboarding"
        verbose_name_plural = "Templates de onboarding"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"], name="onboarding_template_nome_unico_por_empresa"
            )
        ]

    def __str__(self):
        return self.name

    # `task_count` NAO e property: a listagem anota o valor no queryset, e
    # Django nao consegue gravar uma anotacao por cima de uma property —
    # a consulta inteira quebra com "has no setter".


class TemplateTask(models.Model):
    """
    Uma tarefa do roteiro.

    O prazo é relativo (`days_offset` = D+N a partir da admissão), porque o
    template não sabe a data de entrada de ninguém. Vira data absoluta
    apenas na hora de gerar as tarefas.

    O responsável também é relativo: guarda-se o PAPEL, não a pessoa. Um
    template que apontasse para "Maria do RH" pararia de funcionar no dia
    em que a Maria saísse da empresa.
    """

    class Responsible(models.TextChoices):
        EMPLOYEE = "employee", "O próprio colaborador"
        MANAGER = "manager", "Gestor do setor"
        HR = "hr", "RH"

    template = models.ForeignKey(
        OnboardingTemplate, on_delete=models.CASCADE, related_name="tasks"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")

    days_offset = models.PositiveIntegerField(
        default=1, help_text="D+N a partir da admissão. 0 = no próprio dia."
    )
    responsible = models.CharField(
        max_length=10, choices=Responsible.choices, default=Responsible.EMPLOYEE
    )
    priority = models.CharField(
        max_length=10,
        choices=OnboardingTask.Priority.choices,
        default=OnboardingTask.Priority.NORMAL,
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Tarefa do template"
        verbose_name_plural = "Tarefas do template"
        ordering = ["days_offset", "order", "id"]

    def __str__(self):
        return f"D+{self.days_offset} {self.title}"
