from django.db import models


class Sector(models.Model):
    """Setor de uma empresa (ex.: TI, RH, Comercial). Nome único por empresa."""

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="sectors",
        verbose_name="Empresa",
    )
    name = models.CharField(max_length=100, verbose_name="Nome")
    description = models.TextField(blank=True, verbose_name="Descrição")
    manager = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_sectors",
        verbose_name="Gestor responsável",
        help_text="Gestor do setor. Enxerga os colaboradores lotados aqui.",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Ativo",
        help_text="Setor inativo não aparece para novos cadastros, mas preserva o histórico.",
    )

    class Meta:
        verbose_name = "Setor"
        verbose_name_plural = "Setores"
        ordering = ["name"]
        unique_together = [("name", "company")]

    def __str__(self) -> str:
        return self.name


class Position(models.Model):
    """Cargo dentro de um setor (ex.: Desenvolvedor Júnior no setor de TI)."""

    name = models.CharField(max_length=100, verbose_name="Nome")
    description = models.TextField(blank=True, verbose_name="Descrição")
    sector = models.ForeignKey(
        Sector,
        on_delete=models.CASCADE,
        related_name="positions",
        verbose_name="Setor",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Ativo",
        help_text="Cargo inativo não aparece para novos cadastros, mas preserva o histórico.",
    )

    class Meta:
        verbose_name = "Cargo"
        verbose_name_plural = "Cargos"
        ordering = ["sector__name", "name"]
        unique_together = [("name", "sector")]

    def __str__(self) -> str:
        return f"{self.name} — {self.sector.name}"
