from django.db import models


class Material(models.Model):
    """
    Documento ou material de referência (política, manual, organograma).
    Pode ser geral (sector=None) ou específico de um setor.
    """

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="materials",
        verbose_name="Empresa",
    )
    title = models.CharField(max_length=200, verbose_name="Título")
    file_url = models.URLField(verbose_name="URL do arquivo")
    sector = models.ForeignKey(
        "sectors.Sector",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materials",
        verbose_name="Setor",
        help_text="Deixe em branco para materiais gerais (todos os setores).",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Material"
        verbose_name_plural = "Materiais"
        ordering = ["sector__name", "title"]

    def __str__(self) -> str:
        scope = self.sector.name if self.sector else "Geral"
        return f"[{scope}] {self.title}"
