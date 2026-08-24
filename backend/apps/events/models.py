from django.conf import settings
from django.db import models
from django.utils import timezone


class Event(models.Model):
    """
    Evento corporativo: reunião, treinamento presencial, integração.

    `start_at` é DateTimeField e não DateField porque a agenda precisa
    ordenar dois eventos do mesmo dia e mostrar o horário — com data pura,
    "reunião das 9h" e "confraternização das 18h" ficavam empatadas.
    """

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Agendado"
        CANCELLED = "cancelled", "Cancelado"

    company = models.ForeignKey(
        "companies.Company", on_delete=models.CASCADE, related_name="events"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Sala, endereço ou link da reunião.",
    )

    start_at = models.DateTimeField(null=True, blank=True, db_index=True)
    end_at = models.DateTimeField(
        null=True, blank=True, help_text="Opcional. Deve ser depois do início."
    )

    capacity = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Limite de participantes. Vazio = sem limite.",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED, db_index=True
    )
    allows_rsvp = models.BooleanField(
        default=True, help_text="Permite que as pessoas confirmem presença."
    )

    # Segmentação: vazio significa "empresa inteira", mesma semântica dos
    # comunicados — alvo vazio numa dimensão é ausência de restrição.
    target_sectors = models.ManyToManyField(
        "sectors.Sector", blank=True, related_name="targeted_events"
    )
    target_units = models.ManyToManyField(
        "units.Unit", blank=True, related_name="targeted_%(class)ss",
        verbose_name="Unidades",
        help_text="Vazio = todas as unidades da empresa.",
    )

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="organized_events", verbose_name="Organizador",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_at"]
        indexes = [
            models.Index(fields=["company", "status", "start_at"]),
        ]

    def __str__(self):
        quando = self.start_at.date() if self.start_at else "sem data"
        return f"[{self.company.name}] {self.title} - {quando}"

    @property
    def is_past(self) -> bool:
        referencia = self.end_at or self.start_at
        return bool(referencia and referencia < timezone.now())

    @property
    def confirmed_count(self) -> int:
        """Quantos confirmaram presença. Só 'vou' ocupa vaga."""
        anotado = getattr(self, "_confirmed_count", None)
        if anotado is not None:
            return anotado
        return self.attendances.filter(status=EventAttendance.Status.GOING).count()

    @property
    def is_full(self) -> bool:
        if not self.capacity:
            return False
        return self.confirmed_count >= self.capacity

    @property
    def seats_left(self) -> int | None:
        if not self.capacity:
            return None
        return max(self.capacity - self.confirmed_count, 0)


class EventAttendance(models.Model):
    """
    Resposta de uma pessoa a um evento (RSVP).

    Um registro por (evento, pessoa): mudar de ideia atualiza a resposta em
    vez de criar outra linha, então a contagem de confirmados nunca infla.
    """

    class Status(models.TextChoices):
        GOING = "going", "Vou participar"
        NOT_GOING = "not_going", "Não vou participar"

    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="attendances"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="event_attendances"
    )
    status = models.CharField(max_length=20, choices=Status.choices)
    responded_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("event", "user")
        ordering = ["-responded_at"]

    def __str__(self):
        return f"{self.user.email} — {self.get_status_display()} em {self.event.title}"
