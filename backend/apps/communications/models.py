from django.db import models
from django.conf import settings

class Announcement(models.Model):
    """
    Comunicado interno.

    O ciclo de vida (rascunho → agendado → publicado → expirado/arquivado)
    existe para que o RH escreva com calma e escolha quando o texto fica
    visível. Quem publica de fato o agendado é o Celery Beat.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Rascunho'
        SCHEDULED = 'scheduled', 'Agendado'
        PUBLISHED = 'published', 'Publicado'
        EXPIRED = 'expired', 'Expirado'
        ARCHIVED = 'archived', 'Arquivado'

    company = models.ForeignKey('companies.Company', on_delete=models.CASCADE, related_name='announcements')
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_urgent = models.BooleanField(
        default=False,
        help_text='Urgente ignora a preferência de notificação do usuário.',
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    publish_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Quando publicar. Vazio = publicar imediatamente.',
    )
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Depois desta data o comunicado sai do mural.',
    )
    notified_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Marca que as notificações já saíram. Impede envio em duplicidade.',
    )
    
    # Segmentação
    target_sectors = models.ManyToManyField('sectors.Sector', blank=True, related_name='targeted_announcements')
    target_positions = models.ManyToManyField('sectors.Position', blank=True, related_name='targeted_announcements')
    target_units = models.ManyToManyField(
        "units.Unit", blank=True, related_name="targeted_%(class)ss",
        verbose_name="Unidades",
        help_text="Vazio = todas as unidades da empresa.",
    )
    
    # Metadata
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='authored_announcements')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status', '-published_at']),
        ]

    def __str__(self):
        return f"[{self.company.name}] {self.title}"

    @property
    def is_visible(self) -> bool:
        """Publicado e dentro da validade."""
        from django.utils import timezone

        if self.status != self.Status.PUBLISHED:
            return False
        return not (self.expires_at and self.expires_at <= timezone.now())


class AnnouncementRead(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='reads')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='read_announcements')
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('announcement', 'user')

    def __str__(self):
        return f"{self.user.email} leu {self.announcement.title}"
