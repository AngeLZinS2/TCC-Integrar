"""
Unidades (filiais) de uma empresa.

`Company` é o TENANT — a fronteira de isolamento de dados. `Unit` é
localização física dentro dele. Confundir os dois é o erro caro: se cada
filial virasse uma Company, o RH do Grupo São Roque precisaria de três
logins e não conseguiria ver a empresa inteira em lugar nenhum.

A unidade serve para SEGMENTAR (comunicado só da Unidade Centro), nunca
para isolar: quem tem permissão na empresa continua alcançando todas as
unidades dela.
"""

from django.db import models


class Unit(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativa"
        INACTIVE = "inactive", "Inativa"

    company = models.ForeignKey(
        "companies.Company", on_delete=models.CASCADE, related_name="units"
    )
    name = models.CharField(max_length=150)
    code = models.CharField(
        max_length=30, blank=True, default="",
        help_text="Código interno da filial. Opcional.",
    )

    address = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=2, blank=True, default="")

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )

    manager = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_units",
        verbose_name="Responsável pela unidade",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Unidade"
        verbose_name_plural = "Unidades"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"], name="unit_nome_unico_por_empresa"
            ),
            # `code` vazio é o caso comum (campo opcional), e vários vazios
            # não podem colidir — daí a condição.
            models.UniqueConstraint(
                fields=["company", "code"],
                condition=~models.Q(code=""),
                name="unit_codigo_unico_por_empresa",
            ),
        ]

    def __str__(self):
        return f"{self.name} — {self.company.name}"

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE
