from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    Notificação interna do sistema para um colaborador.

    O campo push_token está reservado para integração futura com
    serviços de push (FCM/APNs). Por enquanto fica vazio.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Usuário",
    )
    title = models.CharField(max_length=200, verbose_name="Título")
    message = models.TextField(verbose_name="Mensagem")
    read = models.BooleanField(default=False, verbose_name="Lida", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criada em")

    link = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Destino",
        help_text="Rota do app aberta ao tocar na notificação. Ex.: /documents/12",
    )

    # Reservado para push notifications (FCM/APNs) — fase posterior
    push_token = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Token push",
        help_text="Token do dispositivo para envio de push. Preenchido pelo app Flutter.",
    )

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        status = "✓" if self.read else "●"
        return f"{status} [{self.user}] {self.title}"


class NotificationPreference(models.Model):
    """
    O que cada pessoa quer receber, por canal.

    Um registro por usuário, com um booleano por (canal, categoria). Sem
    registro, o padrão é receber tudo — usuário novo não pode ficar sem
    aviso até descobrir a tela de preferências.

    Notificação crítica ignora estas escolhas: dá para desligar aviso de
    evento, não dá para desligar "sua empresa foi suspensa".
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preference",
        verbose_name="Usuário",
    )

    # ── No app ─────────────────────────────────────────────────────────────
    app_announcements = models.BooleanField(default=True, verbose_name="Comunicados")
    app_requests = models.BooleanField(default=True, verbose_name="Solicitações")
    app_trainings = models.BooleanField(default=True, verbose_name="Treinamentos")
    app_documents = models.BooleanField(default=True, verbose_name="Documentos")
    app_events = models.BooleanField(default=True, verbose_name="Eventos")
    app_tasks = models.BooleanField(default=True, verbose_name="Tarefas")

    # ── Por e-mail ─────────────────────────────────────────────────────────
    email_announcements = models.BooleanField(default=True, verbose_name="Comunicados")
    email_requests = models.BooleanField(default=True, verbose_name="Solicitações")
    email_trainings = models.BooleanField(default=True, verbose_name="Treinamentos")
    email_documents = models.BooleanField(default=True, verbose_name="Documentos")
    email_events = models.BooleanField(default=False, verbose_name="Eventos")
    email_tasks = models.BooleanField(default=True, verbose_name="Tarefas")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Preferência de notificação"
        verbose_name_plural = "Preferências de notificação"

    # Mapa (categoria) -> sufixo do campo. Categoria desconhecida cai no
    # padrão "recebe", para um evento novo nunca nascer silenciado.
    _CAMPO_POR_CATEGORIA = {
        "announcement": "announcements",
        "request": "requests",
        "training": "trainings",
        "document": "documents",
        "event": "events",
        "task": "tasks",
    }

    def allows(self, category: str, canal: str) -> bool:
        sufixo = self._CAMPO_POR_CATEGORIA.get(category)
        if sufixo is None:
            return True
        prefixo = {"in_app": "app", "email": "email"}.get(canal)
        if prefixo is None:
            return True
        return bool(getattr(self, f"{prefixo}_{sufixo}", True))

    def __str__(self) -> str:
        return f"Preferências de {self.user.email}"
