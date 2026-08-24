"""
Serviço de notificação com múltiplos canais.

O Módulo 8 pede a separação: quem decide "houve um evento" não decide
"como avisar". Uma chamada a `notify()` resolve destinatários, respeita
preferências e despacha por canal.

Divisão de responsabilidade:
  - in-app  → sempre síncrono e imediato. É uma linha no banco, o usuário
              espera ver na hora.
  - e-mail  → sempre pela fila. É rede, falha, e precisa de retry. Módulo
              40 é explícito: nunca enviar e-mail dentro de um request.
  - push    → estrutura pronta, sem provedor. Registra e sai.

Notificação crítica ignora preferência: o usuário pode desligar avisos de
evento, mas não pode desligar "seu acesso foi suspenso".
"""

import logging

from django.conf import settings

from .models import Notification, NotificationPreference

logger = logging.getLogger(__name__)


class Category:
    """Categorias que o usuário pode ligar/desligar nas preferências."""

    ANNOUNCEMENT = "announcement"
    REQUEST = "request"
    TRAINING = "training"
    DOCUMENT = "document"
    EVENT = "event"
    TASK = "task"
    SYSTEM = "system"

    ALL = [ANNOUNCEMENT, REQUEST, TRAINING, DOCUMENT, EVENT, TASK, SYSTEM]


def _carregar_preferencias(destinatarios, critico: bool) -> dict:
    """
    {user_id: NotificationPreference} numa query só.

    Consultar por usuário custava DUAS idas ao banco por destinatário (uma
    para o canal in-app, outra para o e-mail) — 1000 queries para avisar uma
    empresa de 500 pessoas, dentro da operação que disparou o aviso.
    """
    if critico:
        return {}
    try:
        return {
            pref.user_id: pref
            for pref in NotificationPreference.objects.filter(
                user_id__in=[u.pk for u in destinatarios]
            )
        }
    except Exception:
        # Falha ao ler preferência não pode calar a notificação: sem o mapa,
        # `_pode_receber` cai no padrão de receber tudo.
        return {}


def _pode_receber(user, category: str, canal: str, critico: bool, preferencias: dict) -> bool:
    """
    Decide pelo mapa já carregado.

    Sem preferência salva, o padrão é receber — um usuário novo não deveria
    ficar sem aviso nenhum até abrir a tela de configurações.
    """
    if critico:
        return True
    pref = preferencias.get(user.pk)
    if pref is None:
        return True
    return pref.allows(category, canal)


def notify(
    users,
    title: str,
    message: str,
    *,
    category: str = Category.SYSTEM,
    email: bool = False,
    critical: bool = False,
    link: str = "",
) -> int:
    """
    Notifica um ou vários usuários.

    `users` aceita um usuário só ou um iterável. Retorna quantas
    notificações in-app foram criadas.
    """
    if hasattr(users, "pk"):
        users = [users]
    destinatarios = [u for u in users if u is not None and u.pk and u.is_active]
    if not destinatarios:
        return 0

    preferencias = _carregar_preferencias(destinatarios, critical)

    # ── in-app: uma query só, mesmo para milhares de pessoas ───────────────
    permitidos_app = [
        u
        for u in destinatarios
        if _pode_receber(u, category, "in_app", critical, preferencias)
    ]
    if permitidos_app:
        Notification.objects.bulk_create(
            [
                Notification(user=u, title=title, message=message, link=link)
                for u in permitidos_app
            ]
        )

    # ── e-mail: sempre pela fila ───────────────────────────────────────────
    if email:
        permitidos_email = [
            u.pk
            for u in destinatarios
            if u.email and _pode_receber(u, category, "email", critical, preferencias)
        ]
        if permitidos_email:
            _enfileirar_email(permitidos_email, title, message)

    return len(permitidos_app)


def _enfileirar_email(user_ids: list[int], subject: str, body: str) -> None:
    """
    Manda o envio para a fila.

    Import tardio para evitar ciclo (tasks importa este módulo). Se o broker
    estiver fora, registra e segue — a notificação in-app já foi criada e a
    operação do usuário não pode falhar por causa de e-mail.
    """
    from .tasks import send_email_notification

    try:
        send_email_notification.delay(user_ids, subject, body)
    except Exception:
        logger.exception(
            "Não foi possível enfileirar e-mail para %d destinatário(s).", len(user_ids)
        )


def notify_company(
    company,
    title: str,
    message: str,
    *,
    category: str = Category.SYSTEM,
    roles: list[str] | None = None,
    email: bool = False,
    link: str = "",
) -> int:
    """Notifica toda a empresa, opcionalmente filtrando por papel."""
    from apps.users.models import User

    usuarios = User.objects.filter(company=company, is_active=True).exclude(role="owner")
    if roles:
        usuarios = usuarios.filter(role__in=roles)
    return notify(
        list(usuarios), title, message, category=category, email=email, link=link
    )


def is_email_enabled() -> bool:
    """True quando há um backend de e-mail que realmente envia."""
    backend = getattr(settings, "EMAIL_BACKEND", "")
    return "dummy" not in backend
