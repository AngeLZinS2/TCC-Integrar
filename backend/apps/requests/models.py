import uuid

from django.db import models, transaction
from django.utils import timezone

from apps.common.uploads import build_storage_path
from apps.companies.models import Company
from apps.users.models import User


def request_attachment_path(instance, filename):
    """
    Anexo de solicitação, particionado por empresa.

    O `filename` recebido é descartado: o nome final é gerado
    internamente, o que impede path traversal e evita que o nome do
    arquivo revele conteúdo sensível no caminho do storage.
    """
    return build_storage_path(
        company_id=instance.comment.request.company_id,
        scope="request_attachments",
        extension=instance.extension or "bin",
    )

class HRRequest(models.Model):
    class Category(models.TextChoices):
        BENEFITS = 'benefits', 'Benefícios'
        DOCUMENTS = 'documents', 'Documentação'
        VACATION = 'vacation', 'Férias'
        ABSENCE = 'absence', 'Ausência'
        EQUIPMENT = 'equipment', 'Equipamento'
        DATA_UPDATE = 'data_update', 'Alteração de Dados'
        OTHER = 'other', 'Outros'

    class Status(models.TextChoices):
        RECEIVED = 'received', 'Recebida'
        IN_REVIEW = 'in_review', 'Em Análise'
        IN_PROGRESS = 'in_progress', 'Em Andamento'
        COMPLETED = 'completed', 'Concluída'
        CANCELLED = 'cancelled', 'Cancelada'

    class Priority(models.TextChoices):
        LOW = 'low', 'Baixa'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'Alta'
        URGENT = 'urgent', 'Urgente'

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='hr_requests')
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_requests')
    # Unico por EMPRESA, nao globalmente: a serie e por tenant, entao
    # SOL-2026-000001 existe uma vez em cada empresa. Unicidade global
    # obrigaria a uma sequencia compartilhada, e ai o numero revelaria o
    # volume total da plataforma para qualquer cliente.
    number = models.CharField(max_length=20, editable=False, db_index=True)
    
    category = models.CharField(max_length=50, choices=Category.choices, default=Category.OTHER)
    subject = models.CharField(max_length=255)
    description = models.TextField()
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_requests')
    
    due_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Prazo de atendimento, derivado da prioridade na abertura.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "number"], name="unique_request_number_per_company"
            )
        ]
        indexes = [
            # A tela do RH filtra por empresa e status e ordena por data.
            models.Index(fields=["company", "status", "-created_at"]),
            models.Index(fields=["requester", "-created_at"]),
            models.Index(fields=["assigned_to", "status"]),
        ]

    # Prazo por prioridade, em horas. Usado para calcular `due_at` e para
    # destacar o que está atrasado na fila do RH.
    SLA_HORAS = {
        Priority.URGENT: 4,
        Priority.HIGH: 24,
        Priority.NORMAL: 72,
        Priority.LOW: 120,
    }

    @property
    def is_overdue(self) -> bool:
        """Atrasada só faz sentido enquanto está em aberto."""
        if self.status in (self.Status.COMPLETED, self.Status.CANCELLED):
            return False
        return bool(self.due_at and self.due_at < timezone.now())

    @property
    def is_open(self) -> bool:
        return self.status not in (self.Status.COMPLETED, self.Status.CANCELLED)

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self._gerar_numero()
        super().save(*args, **kwargs)

    def _gerar_numero(self) -> str:
        """
        Número sequencial por empresa e ano: SOL-2026-000123.

        Sequencial, e não aleatório, porque é o número que a pessoa lê no
        telefone com o RH — "SOL-2026-000123" se dita, "SOL-2026-A7F2C1"
        não. A contagem é por empresa: duas empresas têm a própria série,
        e uma não deduz o volume da outra pelo número.

        A trava é a `unique` da coluna somada ao retry: sob concorrência, o
        segundo insert falha e tenta o número seguinte.
        """
        ano = timezone.localdate().year
        prefixo = f"SOL-{ano}-"
        ultimo = (
            HRRequest.objects.filter(company_id=self.company_id, number__startswith=prefixo)
            .order_by("-number")
            .values_list("number", flat=True)
            .first()
        )
        proximo = 1
        if ultimo:
            try:
                proximo = int(ultimo.rsplit("-", 1)[1]) + 1
            except (ValueError, IndexError):
                proximo = HRRequest.objects.filter(company_id=self.company_id).count() + 1
        return f"{prefixo}{proximo:06d}"

    def __str__(self):
        return f"{self.number} - {self.subject}"


class RequestHistory(models.Model):
    class ActionType(models.TextChoices):
        CREATED = 'created', 'Criou a solicitação'
        ASSIGNED = 'assigned', 'Assumiu o atendimento'
        STATUS_CHANGED = 'status_changed', 'Alterou o status'
        COMMENTED = 'commented', 'Adicionou um comentário'
        CLOSED = 'closed', 'Concluiu a solicitação'
        CANCELLED = 'cancelled', 'Cancelou a solicitação'

    request = models.ForeignKey(HRRequest, on_delete=models.CASCADE, related_name='history')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='request_actions')
    action_type = models.CharField(max_length=50, choices=ActionType.choices)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.request.number} - {self.action_type}"


class RequestComment(models.Model):
    request = models.ForeignKey(HRRequest, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='request_comments')
    text = models.TextField()
    is_internal = models.BooleanField(
        default=False,
        help_text="Nota interna do RH — o solicitante não vê.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comentário de {self.author.email} em {self.request.number}"


class RequestAttachment(models.Model):
    """
    Arquivo anexado a um comentário.

    Passa pela mesma validação dos documentos: allowlist de extensão, MIME
    conferido pelos bytes, tamanho limitado e nome interno gerado. O acesso
    é sempre pela rota de download, que confere a empresa antes de servir.
    """

    comment = models.ForeignKey(
        RequestComment, on_delete=models.CASCADE, related_name="attachments"
    )
    extension = models.CharField(max_length=10, blank=True, default="")
    file = models.FileField(upload_to=request_attachment_path)
    original_name = models.CharField(max_length=150, blank=True, default="")
    mime_type = models.CharField(max_length=100, blank=True, default="")
    size_bytes = models.PositiveBigIntegerField(default=0)
    checksum = models.CharField(max_length=64, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["uploaded_at"]

    def __str__(self):
        return self.original_name or f"anexo {self.pk}"
