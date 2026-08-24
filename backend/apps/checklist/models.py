from django.conf import settings
from django.db import models


class ChecklistItem(models.Model):
    """
    Item do checklist de integração.
    Pode ser geral (sector=None) ou específico de um setor.
    """

    DEADLINE_CHOICES = [
        ("day1", "Dia 1"),
        ("week1", "Semana 1"),
        ("month1", "Mês 1"),
    ]

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="checklist_items",
        verbose_name="Empresa",
    )
    sector = models.ForeignKey(
        "sectors.Sector",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checklist_items",
        verbose_name="Setor",
        help_text="Deixe em branco para itens gerais (todos os setores).",
    )
    title = models.CharField(max_length=200, verbose_name="Título")
    deadline = models.CharField(
        max_length=10,
        choices=DEADLINE_CHOICES,
        verbose_name="Prazo",
        db_index=True,
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Ordem")

    class Meta:
        verbose_name = "Item do checklist"
        verbose_name_plural = "Itens do checklist"
        ordering = ["deadline", "order"]

    def __str__(self) -> str:
        scope = self.sector.name if self.sector else "Geral"
        return f"[{scope} | {self.get_deadline_display()}] {self.title}"


class ChecklistProgress(models.Model):
    """
    Estado de conclusão de um item de checklist por colaborador.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="checklist_progresses",
        verbose_name="Usuário",
    )
    item = models.ForeignKey(
        ChecklistItem,
        on_delete=models.CASCADE,
        related_name="progresses",
        verbose_name="Item",
    )
    completed = models.BooleanField(default=False, verbose_name="Concluído")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Concluído em")

    class Meta:
        verbose_name = "Progresso do checklist"
        verbose_name_plural = "Progressos do checklist"
        unique_together = [("user", "item")]

    def __str__(self) -> str:
        status = "✓" if self.completed else "○"
        return f"{status} {self.user} → {self.item.title}"
