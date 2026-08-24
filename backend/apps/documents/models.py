from django.conf import settings
from django.db import models

from apps.common.uploads import build_storage_path
from apps.companies.models import Company


def document_upload_path(instance, filename):
    """
    Caminho de armazenamento de uma versão.

    O `filename` recebido é ignorado de propósito: o nome final é gerado
    internamente (ver `apps/common/uploads.py`). Guardar o nome enviado
    pelo cliente no caminho seria a porta de entrada para path traversal.
    """
    return build_storage_path(
        company_id=instance.document.company_id,
        scope="documents",
        extension=instance.extension or "bin",
    )


class DocumentCategory(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="document_categories"
    )
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Categoria de documento"
        verbose_name_plural = "Categorias de documento"
        unique_together = ("company", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class Document(models.Model):
    """
    Um documento da biblioteca. O arquivo em si vive nas versões.

    `is_required` marca os que exigem aceite formal. O aceite é registrado
    por VERSÃO — publicar uma versão nova reabre a exigência para todo
    mundo, que é o comportamento pedido no Módulo 5.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        PUBLISHED = "published", "Publicado"
        ARCHIVED = "archived", "Arquivado"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="documents"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        DocumentCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="documents",
    )
    is_required = models.BooleanField(
        default=False, help_text="Exige aceite formal (Li e estou de acordo)"
    )
    target_units = models.ManyToManyField(
        "units.Unit", blank=True, related_name="targeted_%(class)ss",
        verbose_name="Unidades",
        help_text="Vazio = todas as unidades da empresa.",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Depois desta data o documento deixa de ser exibido como vigente.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # A listagem sempre filtra por empresa e status e ordena por data.
            models.Index(fields=["company", "status", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.company.name}] {self.title}"

    @property
    def is_expired(self) -> bool:
        from django.utils import timezone

        return bool(self.expires_at and self.expires_at <= timezone.now())

    def active_version(self):
        return self.versions.filter(is_active=True).first()


class DocumentVersion(models.Model):
    """
    Uma versão do arquivo. Versões antigas nunca são sobrescritas.

    Os metadados de segurança (mime, tamanho, checksum) são gravados na
    validação do upload e servem para auditoria: dá para provar depois que
    o arquivo servido é o mesmo que foi enviado.
    """

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="versions"
    )
    version_number = models.PositiveIntegerField(help_text="ex: 1, 2, 3")

    # Precisa existir antes do upload_to ser chamado — por isso é preenchido
    # no serializer, não em save().
    extension = models.CharField(max_length=10, blank=True, default="")

    file = models.FileField(upload_to=document_upload_path)
    original_name = models.CharField(
        max_length=150, blank=True, default="",
        help_text="Nome enviado pelo usuário. Só para exibição — nunca usado em caminho.",
    )
    mime_type = models.CharField(max_length=100, blank=True, default="")
    size_bytes = models.PositiveBigIntegerField(default=0)
    checksum = models.CharField(
        max_length=64, blank=True, default="",
        help_text="SHA-256 do conteúdo no momento do upload."
    )

    change_note = models.CharField(
        max_length=255, blank=True, default="",
        help_text="O que mudou nesta versão."
    )
    published_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    is_active = models.BooleanField(
        default=True, help_text="Somente uma versão fica vigente por documento."
    )

    class Meta:
        unique_together = ("document", "version_number")
        ordering = ["-version_number"]

    def __str__(self):
        return f"{self.document.title} - v{self.version_number}"

    @property
    def display_name(self) -> str:
        """Nome sugerido no download, sempre com a extensão validada."""
        if self.original_name:
            return self.original_name
        return f"{self.document.title}-v{self.version_number}.{self.extension or 'bin'}"


class DocumentAcceptance(models.Model):
    """
    Registro de "li e estou de acordo".

    Amarrado à VERSÃO, não ao documento: é o que faz uma versão nova exigir
    aceite outra vez, sem apagar o histórico do aceite anterior.

    IP e user agent entram porque são o que dá valor probatório ao aceite.
    Nada além disso é registrado.
    """

    document_version = models.ForeignKey(
        DocumentVersion, on_delete=models.CASCADE, related_name="acceptances"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="accepted_documents"
    )
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ("document_version", "user")
        ordering = ["-accepted_at"]

    def __str__(self):
        return f"{self.user.email} aceitou {self.document_version}"
